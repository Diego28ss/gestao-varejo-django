import json
import math
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from inventario.models import Vendas, Produtos, RupturaEstoque
from inventario.models.configuracoes import ConfiguracaoSistema

def calcular_necessidades_suprimento():
    """ 
    Regra de negócio complexa: Calcula a Velocidade Média de Vendas (VMD), 
    cruza com o estoque atual e soma as rupturas não resolvidas.
    """
    config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
    dias_seguranca = config.dias_seguranca_estoque
    data_inicio = timezone.now() - timedelta(days=14)
    vendas_14d = Vendas.objects.filter(status='VENDA', data_venda__gte=data_inicio)
    
    vendas_por_produto = {}
    for venda in vendas_14d:
        if venda.cupom_texto:
            try:
                itens = json.loads(venda.cupom_texto)
                for item in itens:
                    prod_id = int(item.get('id', 0))
                    qtd = int(item.get('qtd', 0))
                    if prod_id > 0:
                        vendas_por_produto[prod_id] = vendas_por_produto.get(prod_id, 0) + qtd
            except Exception:
                pass

    rupturas_por_produto = RupturaEstoque.objects.filter(resolvido=False).values('produto_id').annotate(total_falta=Sum('quantidade_perdida'))
    mapa_rupturas = {r['produto_id']: r['total_falta'] for r in rupturas_por_produto}
                
    produtos_necessarios = []
    todos_produtos = Produtos.objects.filter(status='ATIVO')
    
    for prod in todos_produtos:
        qtd_vendida = vendas_por_produto.get(prod.id, 0)
        qtd_ruptura = mapa_rupturas.get(prod.id, 0) 
        vmd = qtd_vendida / 14.0 
        qtd_recom = math.ceil(vmd * dias_seguranca) 
        qtd_pedir = (qtd_recom - prod.estoque_atual) + qtd_ruptura
        
        if qtd_pedir > 0 or qtd_ruptura > 0:
            produtos_necessarios.append({
                'id': prod.id, 'nome': prod.nome, 'cod_interno': prod.cod_interno or 'S/C',
                'estoque_atual': prod.estoque_atual, 'qtd_vendida_14d': qtd_vendida,
                'qtd_ruptura': qtd_ruptura, 'qtd_recom': qtd_recom,
                'qtd_pedir': qtd_pedir if qtd_pedir > 0 else qtd_ruptura
            })
            
    produtos_necessarios.sort(key=lambda x: x['qtd_pedir'], reverse=True)
    return produtos_necessarios, dias_seguranca

def resolver_ruptura_estoque(produto_id):
    """ Marca uma ruptura isolada como resolvida """
    RupturaEstoque.objects.filter(produto_id=produto_id, resolvido=False).update(resolvido=True)

def registrar_encomenda_produto(produto_id, qtd, data_previsao):
    """ Alimenta o trânsito de um produto e resolve suas rupturas """
    if not qtd or not data_previsao: 
        raise ValueError('Quantidade e Data são obrigatórios.')
        
    produto = Produtos.objects.get(id=produto_id)
    produto.qtd_em_transito = int(qtd)
    produto.data_previsao_chegada = data_previsao
    produto.save()
    RupturaEstoque.objects.filter(produto=produto, resolvido=False).update(resolvido=True)

def processar_carrinho_gerente(itens):
    """ Processa o fechamento em lote do carrinho de suprimentos do Gerente """
    with transaction.atomic():
        for item in itens:
            produto_id = item.get('id')
            qtd = int(item.get('qtd', 0))
            data_previsao = item.get('data')
            if produto_id and qtd > 0:
                produto = Produtos.objects.get(id=produto_id)
                produto.qtd_em_transito = qtd
                produto.data_previsao_chegada = data_previsao
                produto.save()
                RupturaEstoque.objects.filter(produto=produto, resolvido=False).update(resolvido=True)
                