from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.vendas import relatorios_service
from inventario.models import Vendas, Usuarios
from django.db.models import Sum
from datetime import datetime

# ==========================================
# 📊 RELATÓRIOS VIEWS (THIN VIEWS)
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_mes = request.GET.get('mes', '')

    vendas, faturamento, qtd_vendas, ticket_medio = relatorios_service.obter_dados_relatorio_vendas(filtro_vendedor, filtro_mes)
    vendedores = relatorios_service.obter_vendedores()
    lista_meses = relatorios_service.obter_lista_meses()

    return render(request, 'inventario/relatorios.html', {
        'vendas': vendas,
        'vendedores': vendedores,
        'faturamento': faturamento,
        'qtd_vendas': qtd_vendas,
        'ticket_medio': ticket_medio,
        'filtro_vendedor': filtro_vendedor,
        'filtro_mes': filtro_mes,
        'lista_meses': lista_meses
    })

def imprimir_cupom(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')
    
    venda, itens, loja = relatorios_service.obter_dados_impressao_cupom(id)
    
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens, 'loja': loja})

def imprimir_cupom_a4(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    venda, itens, loja = relatorios_service.obter_dados_impressao_cupom(id)
    
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens, 'loja': loja})


# ==========================================
# 🚀 NOVO: EXTRATO DETALHADO DE COMISSÕES (Fase 8)
# ==========================================
def relatorio_comissao(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    vendedor_selecionado = request.GET.get('vendedor', '').strip()
    hoje = datetime.today()
    
    # 🚀 Proteção: Força o mês e ano atual se o campo vier vazio na URL
    try:
        mes_selecionado = int(request.GET.get('mes') or hoje.month)
    except ValueError:
        mes_selecionado = hoje.month
        
    try:
        ano_selecionado = int(request.GET.get('ano') or hoje.year)
    except ValueError:
        ano_selecionado = hoje.year

    meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'},
    ]

    vendedores = Usuarios.objects.exclude(perfil='DEV').order_by('login')
    
    # Filtra as vendas (apenas faturadas/finalizadas no PDV)
    vendas_queryset = Vendas.objects.filter(
        status__in=['FATURADO', 'VENDA'],
        data_venda__year=ano_selecionado,
        data_venda__month=mes_selecionado
    ).order_by('-data_venda')

    if vendedor_selecionado:
        # 🚀 Correção: '__iexact' faz com que 'diego', 'Diego' ou 'DIEGO' sejam todos aceitos
        vendas_queryset = vendas_queryset.filter(vendedor__iexact=vendedor_selecionado)

    lista_vendas_extrato = []
    total_geral_comissao = 0.00
    total_geral_vendas_bruto = 0.00
    
    for v in vendas_queryset:
        v_bruto = float(v.valor_total) or 0.00
        total_geral_vendas_bruto += v_bruto
        
        desc_comum = float(v.desconto_comum) if getattr(v, 'desconto_comum', None) else 0.00
        desc_pontos = float(v.desconto_pontos) if getattr(v, 'desconto_pontos', None) else 0.00
        
        v_liquido = v_bruto - desc_comum - desc_pontos
        if v_liquido < 0: v_liquido = 0
        
        perc_comissao = float(v.percentual_comissao) if getattr(v, 'percentual_comissao', None) else 0.00
        valor_comissao = v_liquido * (perc_comissao / 100.0)
        
        total_geral_comissao += valor_comissao
        
        lista_vendas_extrato.append({
            'id': v.id,
            'data': v.data_venda,
            'vendedor': v.vendedor,
            'percentual': perc_comissao,
            'valor_bruto': v_bruto,
            'desc_comum': desc_comum,
            'desc_pontos': desc_pontos,
            'valor_liquido': v_liquido,
            'comissao': valor_comissao
        })

    return render(request, 'inventario/relatorio_comissao.html', {
        'vendedores': vendedores,
        'meses': meses,
        'vendedor_selecionado': vendedor_selecionado,
        'mes_selecionado': mes_selecionado,
        'ano_selecionado': ano_selecionado,
        'extrato': lista_vendas_extrato,
        'total_geral_vendas': total_geral_vendas_bruto,
        'total_geral_comissao': total_geral_comissao
    })

