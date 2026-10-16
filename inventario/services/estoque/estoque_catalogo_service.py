from django.db import connections
from inventario.models import Produtos, AlertaPreco, RelacaoEmbalagensTintometrico

def gerar_codigo_interno():
    """ Gera um novo código interno sequencial com 6 dígitos automaticamente """
    codigos_existentes = Produtos.objects.values_list('cod_interno', flat=True)
    numericos = [int(c) for c in codigos_existentes if c and c.isdigit()]
    proximo_numero = max(numericos) + 1 if numericos else 1
    novo_codigo = str(proximo_numero).zfill(6)
    
    while Produtos.objects.filter(cod_interno=novo_codigo).exists():
        proximo_numero += 1
        novo_codigo = str(proximo_numero).zfill(6)
    return novo_codigo

def verificar_duplicidade_cod_barras(cod_barras, produto_id=None):
    """ Verifica se o código de barras já existe noutro produto para evitar conflitos no PDV """
    if not cod_barras or cod_barras.upper() == 'SEM GTIN':
        return None
    query = Produtos.objects.filter(cod_barras=cod_barras)
    if produto_id:
        query = query.exclude(id=produto_id)
    return query.first()

def processar_salvamento_produto(produto_salvo, dados, produto_id, custo_antigo, venda_antigo):
    """ Aplica as regras de negócio de gravação: alertas de preço, dados fiscais e sistema tintométrico """
    # Injeção dos dados fiscais exigidos pela NFe
    produto_salvo.cst_csosn = dados.get('cst_csosn', '').strip()
    produto_salvo.cfop_especifico = dados.get('cfop_especifico', '').strip()
    produto_salvo.cest = dados.get('cest', '').strip()
    produto_salvo.cod_forn = dados.get('cod_forn', '').strip()
    produto_salvo.aviso_estoque = ""
    produto_salvo.save()
    
    # Gera alerta de preço para troca de etiqueta na gôndola se o preço de venda mudou
    if produto_id:
        if round(float(produto_salvo.preco_venda or 0), 2) != round(venda_antigo, 2):
            AlertaPreco.objects.create(
                produto=produto_salvo,
                custo_anterior=custo_antigo,
                custo_novo=produto_salvo.preco_custo,
                venda_anterior=venda_antigo,
                venda_novo=produto_salvo.preco_venda,
                origem='MANUAL'
            )
            
    # Integração complexa com o banco de dados Tintométrico secundário
    es_base = dados.get('es_base_tintometrico') == 'on'
    base_sel = dados.get('base_tintometrico_selecionada')
    tamanho_sel = dados.get('tamanho_tintometrico_selecionado')
    es_corante = dados.get('es_corante_tintometrico') == 'on'
    corante_sel = dados.get('corante_tintometrico_selecionado')
    
    RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
        produto_cod_interno_id=produto_salvo.cod_interno
    ).delete()
    
    if es_base and base_sel and tamanho_sel:
        RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').update_or_create(
            codigo_base_tintometrico=base_sel,
            tamanho_codigo=tamanho_sel,
            defaults={'produto_cod_interno_id': produto_salvo.cod_interno}
        )
        
    with connections['tintometrico_db'].cursor() as cursor:
        cursor.execute("UPDATE corantes SET produto_cod_interno = NULL WHERE produto_cod_interno = %s", [produto_salvo.cod_interno])
        if es_corante and corante_sel:
            cursor.execute("UPDATE corantes SET produto_cod_interno = %s WHERE id_formula = %s", [produto_salvo.cod_interno, corante_sel])

    return produto_salvo

def inativar_produto(produto_id):
    """ Muda o status do produto para INATIVO, impedindo a sua venda sem o deletar do histórico """
    from django.shortcuts import get_object_or_404
    produto = get_object_or_404(Produtos, id=produto_id)
    produto.status = 'INATIVO'
    produto.save(update_fields=['status'])
    return produto

def obter_dados_tintometrico():
    """ Busca as bases, embalagens e corantes do banco tintométrico para renderizar o catálogo """
    bases, tamanhos, mapa_vinculos, corantes, mapa_vinculos_pigmentos = [], [], {}, [], {}

    try:
        ordem_embalagens = [1, 2, 3, 7, 8, 39, 21, 32, 9, 10, 28, 29, 30, 35, 36, 37, 38, 40, 41]
        with connections['tintometrico_db'].cursor() as cursor:
            cursor.execute("SELECT DISTINCT nome_base FROM bases WHERE nome_base IS NOT NULL ORDER BY nome_base")
            bases = [row[0].strip() for row in cursor.fetchall() if row[0]]

            placeholders = ', '.join(['%s'] * len(ordem_embalagens))
            cursor.execute(f"SELECT id_emb, tamanho FROM embalagens WHERE id_emb IN ({placeholders})", ordem_embalagens)
            embalagens_banco = {row[0]: row[1].strip() for row in cursor.fetchall() if row[1]}
            
            for id_emb in ordem_embalagens:
                if id_emb in embalagens_banco:
                    tamanhos.append(embalagens_banco[id_emb])
                    
            vinculos_existentes = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').all()
            for v in vinculos_existentes:
                mapa_vinculos[v.produto_cod_interno_id] = {
                    'codigo_base_tintometrico': v.codigo_base_tintometrico,
                    'tamanho_codigo': v.tamanho_codigo
                }
                
            cursor.execute("SELECT id_formula, letra_codigo, nome_pigmento FROM corantes ORDER BY letra_codigo")
            for row in cursor.fetchall():
                corantes.append({'id_formula': row[0], 'letra': row[1], 'nome': row[2]})

            cursor.execute("SELECT produto_cod_interno, id_formula FROM corantes WHERE produto_cod_interno IS NOT NULL")
            for row in cursor.fetchall():
                mapa_vinculos_pigmentos[row[0]] = row[1]
                
    except Exception as e:
        pass
        
    return bases, tamanhos, mapa_vinculos, corantes, mapa_vinculos_pigmentos
