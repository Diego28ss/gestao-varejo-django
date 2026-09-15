from django.shortcuts import render, redirect
from inventario.models import Noticias, Produtos, RupturaEstoque, AlertaPreco

# ==========================================
# 📊 PAINEL PRINCIPAL
# ==========================================

def painel_principal(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # Busca as últimas 5 notícias ativas, da mais nova para a mais velha
    ultimas_noticias = Noticias.objects.filter(ativo=True).order_by('-data_publicacao')[:5]

    # 🚀 CÁLCULO DA MISSÃO MATINAL
    ids_ruptura = list(RupturaEstoque.objects.filter(resolvido=False).values_list('produto_id', flat=True))
    ids_negativos = list(Produtos.objects.filter(estoque_atual__lt=0, status='ATIVO').values_list('id', flat=True))
    total_pendente = len(set(ids_ruptura + ids_negativos))

    # 🚀 CÁLCULO DOS ALERTAS DE PREÇO (NOVO)
    total_alertas_preco = AlertaPreco.objects.filter(resolvido=False).count()

    context = {
        'noticias_mural': ultimas_noticias,
        'total_auditoria_pendente': total_pendente,
        'total_alertas_preco': total_alertas_preco, # Enviando para o HTML piscar o aviso
    }
    
    return render(request, 'inventario/index.html', context)
