from inventario.models import Noticias, Produtos, RupturaEstoque, AlertaPreco

def obter_dados_painel():
    """ Concentra todas as métricas e regras de negócio da tela inicial """
    
    # 1. Busca as últimas 5 notícias ativas
    ultimas_noticias = Noticias.objects.filter(ativo=True).order_by('-data_publicacao')[:5]

    # 2. Cálculo da Missão Matinal (Rupturas + Estoques Negativos)
    ids_ruptura = list(RupturaEstoque.objects.filter(resolvido=False).values_list('produto_id', flat=True))
    ids_negativos = list(Produtos.objects.filter(estoque_atual__lt=0, status='ATIVO').values_list('id', flat=True))
    total_pendente = len(set(ids_ruptura + ids_negativos))

    # 3. Cálculo dos Alertas de Preço
    total_alertas_preco = AlertaPreco.objects.filter(resolvido=False).count()

    return {
        'noticias_mural': ultimas_noticias,
        'total_auditoria_pendente': total_pendente,
        'total_alertas_preco': total_alertas_preco,
    }
