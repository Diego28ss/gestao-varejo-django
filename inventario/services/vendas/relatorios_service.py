import json
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from inventario.models import Vendas, Usuarios
from inventario.models.configuracoes import ConfiguracaoEmissor

def obter_vendedores():
    # Retorna todos os usuários cadastrados, ignorando os de perfil DEV
    return Usuarios.objects.exclude(perfil='DEV')

def obter_lista_meses():
    # Retorna uma lista estática de dicionários para montar o filtro de meses no frontend
    return [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'}
    ]

def obter_dados_relatorio_vendas(filtro_vendedor=None, filtro_mes=None):
    # Filtra as vendas válidas (faturadas ou finalizadas) e aplica os filtros recebidos do frontend
    queryset = Vendas.objects.filter(status__in=['FATURADO', 'VENDA', 'FINALIZADO']).order_by('-id')

    if filtro_vendedor and filtro_vendedor.strip():
        queryset = queryset.filter(vendedor__icontains=filtro_vendedor.strip())
    
    if filtro_mes and filtro_mes.isdigit():
        queryset = queryset.filter(data_venda__month=int(filtro_mes))

    # Calcula as métricas financeiras do topo do painel
    faturamento = queryset.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    qtd_vendas = queryset.count()
    ticket_medio = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0

    return queryset, faturamento, qtd_vendas, ticket_medio

def obter_dados_impressao_cupom(venda_id):
    # Busca a venda específica, converte os itens de JSON para Python e traz os dados da loja
    venda = get_object_or_404(Vendas, id=venda_id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    loja = ConfiguracaoEmissor.objects.first()
    
    return venda, itens, loja
