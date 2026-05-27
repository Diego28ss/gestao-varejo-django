import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from inventario.models import Vendas, Produtos, Usuarios

# ==========================================
# 📊 RELATÓRIOS E CANCELAMENTOS
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    queryset = Vendas.objects.all().order_by('-id')
    vendedores = Usuarios.objects.all()

    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_status = request.GET.get('status', '')

    if filtro_vendedor and filtro_vendedor.strip():
        queryset = queryset.filter(vendedor__icontains=filtro_vendedor.strip())
    
    if filtro_status and filtro_status.strip():
        queryset = queryset.filter(status=filtro_status.strip())

    # Cálculos Dinâmicos
    faturamento = queryset.filter(status='VENDA').aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    qtd_vendas = queryset.filter(status='VENDA').count()
    qtd_orcamentos = queryset.filter(status='ORCAMENTO').count()
    ticket_medio = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0

    return render(request, 'inventario/relatorios.html', {
        'vendas': queryset,
        'vendedores': vendedores,
        'faturamento': faturamento,
        'qtd_vendas': qtd_vendas,
        'qtd_orcamentos': qtd_orcamentos,
        'ticket_medio': ticket_medio,
        'filtro_vendedor': filtro_vendedor,
        'filtro_status': filtro_status
    })

def imprimir_cupom(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')
    
    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens})

def imprimir_cupom_a4(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens})

def cancelar_venda(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        venda_id = request.POST.get('venda_id')
        motivo = request.POST.get('motivo')

        if not venda_id or not str(venda_id).isdigit():
            messages.error(request, "ID de venda inválido.")
            return redirect('tela_relatorios')

        venda = get_object_or_404(Vendas, id=venda_id)

        if venda.status == 'CANCELADA':
            messages.warning(request, f"A venda #{venda_id} já está cancelada.")
            return redirect('tela_relatorios')

        venda.status = 'CANCELADA'
        venda.save()

        # Estorno de Estoque
        try:
            itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
            for item in itens:
                produto_id = item.get('id')
                if produto_id and str(produto_id).isdigit():
                    produto = Produtos.objects.filter(id=int(produto_id)).first()
                    if produto:
                        produto.estoque_atual += int(item.get('qtd', 0))
                        produto.save()
            messages.success(request, f"Venda #{venda_id} cancelada com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao estornar estoque: {str(e)}")
        
    return redirect('tela_relatorios')
