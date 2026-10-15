import json
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from inventario.models import InventarioSessao, InventarioItem, Vendas, Kardex, Produtos, RupturaEstoque

def criar_snapshot_dinamico(usuario, marca_obj, familia_obj, unidade):
    """ Cria o lote e congela o estoque atual para auditoria """
    query = Q(status='ATIVO')
    if marca_obj: query &= Q(marca=marca_obj)
    if familia_obj: query &= Q(familia=familia_obj)
    if unidade: query &= Q(unidade__iexact=unidade.strip())
    
    produtos_alvo = Produtos.objects.filter(query)

    # TRAVA: Sobreposição de Área
    produtos_em_contagem = InventarioItem.objects.filter(
        sessao__status='ABERTO', 
        produto__in=produtos_alvo
    ).values_list('produto__nome', flat=True)

    if produtos_em_contagem.exists():
        nomes_conflito = ", ".join(list(produtos_em_contagem)[:2])
        raise ValueError(f"BLOQUEIO: Produtos já estão noutro inventário aberto (Ex: {nomes_conflito}...). Termine-o primeiro.")
    
    novo_lote = InventarioSessao.objects.create(
        criado_por=usuario, status='ABERTO',
        filtro_marca=marca_obj, filtro_familia=familia_obj, filtro_unidade=unidade
    )
    
    itens_snapshot = [
        InventarioItem(sessao=novo_lote, produto=p, saldo_sistema=p.estoque_atual, saldo_fisico=0, contado=False)
        for p in produtos_alvo
    ]
    InventarioItem.objects.bulk_create(itens_snapshot)
    
    return novo_lote, len(itens_snapshot)

def registrar_bipagem_dinamica(sessao_id, codigo, qtd):
    """ Adiciona contagem física a um item do lote via Leitor de Código de Barras """
    produto = Produtos.objects.filter(Q(cod_barras=codigo) | Q(cod_interno=codigo)).first()
    if not produto:
        raise ValueError(f'Código {codigo} não encontrado.')
    
    item = InventarioItem.objects.filter(sessao_id=sessao_id, produto=produto).first()
    if not item:
        raise ValueError(f'O produto {produto.nome} não pertence aos filtros deste lote!')
    
    item.saldo_fisico += qtd
    item.contado = True
    item.save(update_fields=['saldo_fisico', 'contado'])
    return produto

def reduzir_bipagem_dinamica(sessao_id, produto_id):
    """ Remove 1 unidade da contagem física (correção de erro do utilizador) """
    item = InventarioItem.objects.filter(sessao_id=sessao_id, produto_id=produto_id).first()
    if not item:
        raise ValueError('Item não encontrado neste lote.')

    if item.saldo_fisico > 0:
        item.saldo_fisico -= 1
        if item.saldo_fisico == 0:
            item.contado = False
        item.save(update_fields=['saldo_fisico', 'contado'])
        return True
    raise ValueError('A contagem já está zerada.')

def atualizar_quantidade_dinamica(sessao_id, produto_id, nova_qtd):
    """ Atualiza a quantidade exata digitada diretamente na tabela """
    item = InventarioItem.objects.filter(sessao_id=sessao_id, produto_id=produto_id).first()
    if not item:
        raise ValueError('Item não encontrado neste lote.')

    item.saldo_fisico = nova_qtd
    item.contado = nova_qtd > 0
    item.save(update_fields=['saldo_fisico', 'contado'])
    return True

def conciliar_e_finalizar_inventario(sessao_id, acao_omissos):
    """ A Grande Matemática: Reconciliação do Físico com as Vendas durante a contagem """
    sessao = InventarioSessao.objects.get(id=sessao_id)

    if not acao_omissos:
        qtd_omissos = InventarioItem.objects.filter(sessao=sessao, contado=False).count()
        if qtd_omissos > 0:
            return {'status': 'pendente_omissos', 'quantidade': qtd_omissos}
        acao_omissos = 'IGNORAR' 
    
    sessao.status = 'FINALIZADO'
    sessao.data_finalizacao = timezone.now()
    
    vendas_periodo = Vendas.objects.filter(
        status__in=['FATURADO', 'FINALIZADO'],
        data_venda__gte=sessao.data_inicio,
        data_venda__lte=sessao.data_finalizacao
    )
    
    mapa_vendas = {}
    for v in vendas_periodo:
        if v.cupom_texto:
            try:
                carrinho = json.loads(v.cupom_texto)
                for it in carrinho:
                    p_id = int(it.get('id', 0))
                    if p_id > 0:
                        mapa_vendas[p_id] = mapa_vendas.get(p_id, 0) + int(it.get('qtd', 0))
            except: pass
    
    total_sobra = 0.0
    total_perda = 0.0
    kardex_list = []
    ids_contados = []

    itens = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
    
    with transaction.atomic():
        for item in itens:
            produto = item.produto
            
            if not item.contado and acao_omissos == 'ZERAR':
                item.saldo_fisico = 0
                item.contado = True
                item.save(update_fields=['saldo_fisico', 'contado'])

            if not item.contado:
                continue

            ids_contados.append(produto.id)
            qtd_vendida = mapa_vendas.get(produto.id, 0)
            
            esperado_na_prateleira = item.saldo_sistema - qtd_vendida
            qtd_ajuste = item.saldo_fisico - esperado_na_prateleira
            
            novo_estoque = item.saldo_fisico - qtd_vendida
            if novo_estoque < 0: novo_estoque = 0 
            
            if qtd_ajuste != 0: 
                custo = float(produto.preco_custo or 0.0)
                valor_ajuste = abs(qtd_ajuste) * custo
                
                if qtd_ajuste > 0:
                    total_sobra += valor_ajuste
                    tipo_mov = 'AJUSTE (SOBRA)'
                else:
                    total_perda += valor_ajuste
                    tipo_mov = 'AJUSTE (PERDA)'
                    
                kardex_list.append(Kardex(
                    produto=produto,
                    tipo_movimento=tipo_mov,
                    quantidade=qtd_ajuste,
                    saldo_anterior=item.saldo_sistema, 
                    saldo_novo=novo_estoque,
                    motivo=f"Inventário Rotativo #{sessao.id}",
                    operador=sessao.criado_por,
                    custo_unitario=custo,
                    valor_total=valor_ajuste
                ))

            produto.estoque_atual = novo_estoque
            produto.save(update_fields=['estoque_atual'])
        
        if kardex_list:
            Kardex.objects.bulk_create(kardex_list)

        sessao.valor_sobra = total_sobra
        sessao.valor_perda = total_perda
        sessao.save(update_fields=['status', 'data_finalizacao', 'valor_sobra', 'valor_perda'])
        
        if ids_contados:
            RupturaEstoque.objects.filter(produto_id__in=ids_contados, resolvido=False).update(resolvido=True)
            
    return {'status': 'sucesso'}
