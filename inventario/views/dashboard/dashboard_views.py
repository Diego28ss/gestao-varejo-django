from django.shortcuts import render, redirect
from inventario.services.dashboard.dashboard_service import obter_dados_painel

def painel_principal(request):
    """ View Fina: Apenas renderiza os dados calculados pelo Service """
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # O Service entrega o dicionário pronto para o template HTML
    context = obter_dados_painel()
    
    return render(request, 'inventario/index.html', context)
