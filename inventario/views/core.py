from django.shortcuts import render, redirect
from inventario.models import Noticias

# ==========================================
# 📊 PAINEL PRINCIPAL
# ==========================================

def painel_principal(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # 🚀 Busca as últimas 5 notícias ativas, da mais nova para a mais velha
    ultimas_noticias = Noticias.objects.filter(ativo=True).order_by('-data_publicacao')[:5]

    context = {
        'noticias_mural': ultimas_noticias,
    }
    
    return render(request, 'inventario/index.html', context)
