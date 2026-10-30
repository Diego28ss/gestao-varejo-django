from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.vendas import relatorios_service

# ==========================================
# 📊 RELATÓRIOS VIEWS (THIN VIEWS)
# ==========================================

def tela_relatorios(request):
    # Protege a rota garantindo que apenas utilizadores logados acedem
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # Captura os parâmetros de filtro da URL
    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_mes = request.GET.get('mes', '')

    # Delega as consultas complexas e cálculos para a camada de serviço
    vendas, faturamento, qtd_vendas, ticket_medio = relatorios_service.obter_dados_relatorio_vendas(filtro_vendedor, filtro_mes)
    vendedores = relatorios_service.obter_vendedores()
    lista_meses = relatorios_service.obter_lista_meses()

    # Envia os dados processados para renderização no template
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
    # Valida se o ID fornecido na URL é numérico e válido
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')
    
    # Chama o serviço para buscar os dados consolidados da venda
    venda, itens, loja = relatorios_service.obter_dados_impressao_cupom(id)
    
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens, 'loja': loja})

def imprimir_cupom_a4(request, id=None):
    # Valida se o ID fornecido na URL é numérico e válido
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    # Reutiliza o mesmo serviço do cupom térmico para renderizar o formato A4
    venda, itens, loja = relatorios_service.obter_dados_impressao_cupom(id)
    
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens, 'loja': loja})
