import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from inventario.models import Vendas, Usuarios
from inventario.models.configuracoes import ConfiguracaoEmissor

# ==========================================
# 📊 RELATÓRIOS (APENAS FATURADOS)
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    queryset = Vendas.objects.filter(status__in=['FATURADO', 'VENDA', 'FINALIZADO']).order_by('-id')
    vendedores = Usuarios.objects.exclude(perfil='DEV')

    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_mes = request.GET.get('mes', '')

    if filtro_vendedor and filtro_vendedor.strip():
        queryset = queryset.filter(vendedor__icontains=filtro_vendedor.strip())
    
    if filtro_mes and filtro_mes.isdigit():
        queryset = queryset.filter(data_venda__month=int(filtro_mes))

    faturamento = queryset.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    qtd_vendas = queryset.count()
    ticket_medio = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0

    lista_meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'}
    ]

    return render(request, 'inventario/relatorios.html', {
        'vendas': queryset,
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
    
    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    loja = ConfiguracaoEmissor.objects.first()
    
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens, 'loja': loja})

def imprimir_cupom_a4(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    loja = ConfiguracaoEmissor.objects.first()
    
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens, 'loja': loja})
