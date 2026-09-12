from django.shortcuts import render, redirect
from inventario.models import Noticias, Produtos, RupturaEstoque

# ==========================================
# 📊 PAINEL PRINCIPAL
# ==========================================

def painel_principal(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # Busca as últimas 5 notícias ativas, da mais nova para a mais velha
    ultimas_noticias = Noticias.objects.filter(ativo=True).order_by('-data_publicacao')[:5]

    # 🚀 CÁLCULO DA MISSÃO MATINAL (Rupturas não resolvidas + Estoques negativos)
    # 1. Pega os IDs dos produtos com ruptura pendente informada no PDV
    ids_ruptura = list(RupturaEstoque.objects.filter(resolvido=False).values_list('produto_id', flat=True))
    
    # 2. Pega os IDs dos produtos que o sistema está com estoque negativo
    ids_negativos = list(Produtos.objects.filter(estoque_atual__lt=0, status='ATIVO').values_list('id', flat=True))
    
    # 3. Une as duas listas e remove duplicatas (caso um produto tenha os dois problemas)
    total_pendente = len(set(ids_ruptura + ids_negativos))

    context = {
        'noticias_mural': ultimas_noticias,
        'total_auditoria_pendente': total_pendente, # 🚀 Aciona o alerta piscante no HTML!
    }
    
    return render(request, 'inventario/index.html', context)
