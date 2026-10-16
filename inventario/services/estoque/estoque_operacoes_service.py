import random
from django.db.models import Q
from inventario.models import Produtos, AlertaPreco

def gerar_auditoria_aleatoria(limite=5):
    """ Sorteia produtos ativos e com saldo para a missão matinal de contagem """
    produtos_elegiveis = Produtos.objects.filter(status='ATIVO', estoque_atual__gt=0)
    lista_produtos = list(produtos_elegiveis)
    
    if not lista_produtos:
        return []
    
    qtd_sorteio = min(len(lista_produtos), limite)
    return random.sample(lista_produtos, qtd_sorteio)

def resolver_alerta_gondola(alerta_id):
    """ Marca um alerta de preço como resolvido após a etiqueta ser impressa """
    alerta = AlertaPreco.objects.filter(id=alerta_id, resolvido=False).first()
    if not alerta:
        raise ValueError("Alerta não encontrado ou já resolvido.")
    
    alerta.resolvido = True
    alerta.save(update_fields=['resolvido'])
    
    # Se o alerta veio do robô de entrada de notas (BAIXA_CUSTO), limpa o aviso do produto
    if alerta.origem == 'AUTOMATICA':
        produto = alerta.produto
        if produto.aviso_estoque and 'BAIXA_CUSTO' in produto.aviso_estoque:
            produto.aviso_estoque = ""
            produto.save(update_fields=['aviso_estoque'])
            
    return True

def buscar_produto_para_etiqueta(codigo):
    """ Busca um produto específico pelo código (barras ou interno) para a fila de impressão """
    codigo_str = str(codigo).strip()
    produto = Produtos.objects.filter(Q(cod_barras=codigo_str) | Q(cod_interno=codigo_str)).first()
    
    if not produto:
        raise ValueError(f"O código '{codigo_str}' não foi encontrado no sistema.")
        
    return produto
