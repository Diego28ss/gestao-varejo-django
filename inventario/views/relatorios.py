import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum

# Importação dos modelos necessários para relatórios e estornos
from inventario.models import Vendas, Produtos

# ==========================================
# 📊 RELATÓRIOS, IMPRESSÃO E CANCELAMENTOS
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # Procura todas as vendas registadas, ordenando das mais recentes para as mais antigas
    vendas = Vendas.objects.all().order_by('-id')

    # Filtra apenas as vendas ativas para calcular as métricas financeiras
    vendas_ativas = vendas.filter(status='VENDA')
    
    # Executa a soma dos valores totais e descontos diretamente na base de dados
    total_faturamento = vendas_ativas.aggregate(total=Sum('valor_total'))['total'] or 0.0
    total_descontos = vendas_ativas.aggregate(total=Sum('valor_desconto'))['total'] or 0.0
    qtd_vendas = vendas_ativas.count()

    context = {
        'vendas': vendas,
        'total_faturamento': total_faturamento,
        'total_descontos': total_descontos,
        'qtd_vendas': qtd_vendas,
    }
    return render(request, 'inventario/relatorios.html', context)


def imprimir_cupom(request, id):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    venda = get_object_or_404(Vendas, id=id)

    # Descodifica a string JSON do carrinho para listar os produtos no cupão
    try:
        itens = json.loads(venda.cupom_texto)
    except Exception:
        itens = []

    return render(request, 'inventario/cupom_nao_fiscal.html', {
        'venda': venda,
        'itens': itens
    })


def imprimir_cupom_a4(request, id):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    venda = get_object_or_404(Vendas, id=id)

    try:
        itens = json.loads(venda.cupom_texto)
    except Exception:
        itens = []

    return render(request, 'inventario/cupom_a4.html', {
        'venda': venda,
        'itens': itens
    })


def cancelar_venda(request, id):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    venda = get_object_or_404(Vendas, id=id)

    if venda.status == 'CANCELADA':
        messages.warning(request, f"A venda #{id} já se encontra cancelada.")
        return redirect('tela_relatorios')

    # Altera o estado da venda
    venda.status = 'CANCELADA'
    venda.save()

    # Processa o estorno automático dos produtos devolvidos para o stock
    try:
        itens = json.loads(venda.cupom_texto)
        for item in itens:
            produto_id = item.get('id')
            qtd_devolvida = int(item.get('qtd', 0))

            if produto_id and qtd_devolvida > 0:
                produto = Produtos.objects.filter(id=produto_id).first()
                if produto:
                    produto.estoque_atual += qtd_devolvida
                    produto.save()
                    
        messages.success(request, f"Venda #{id} cancelada e produtos estornados no stock com sucesso!")
    except Exception as e:
        print(f"Erro ao estornar stock no cancelamento: {e}")
        messages.success(request, f"Venda #{id} alterada para cancelada, mas houve um problema no estorno automático.")

    return redirect('tela_relatorios')
