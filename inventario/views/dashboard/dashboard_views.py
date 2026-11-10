import json
from django.shortcuts import render, redirect
from inventario.services.dashboard.dashboard_service import obter_dados_painel

def painel_principal(request):
    """ View Fina: Renderiza os dados calculados pelo Service (incluindo o gráfico) """
    if 'usuario_logado' not in request.session:
        return redirect('login')

    context = obter_dados_painel()
    
    # Converte as listas do Python para JSON Strings seguras para o Chart.js ler no template
    context['graf_labels'] = json.dumps(context['graf_labels'])
    context['graf_valores'] = json.dumps(context['graf_valores'])
    
    return render(request, 'inventario/index.html', context)