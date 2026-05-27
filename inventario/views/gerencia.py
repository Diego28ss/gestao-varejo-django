from django.shortcuts import render, redirect

def tela_painel_gerencia(request):
    """
    Controla o acesso à tela centralizadora do Painel de Gerência.
    """
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    return render(request, 'inventario/painel_gerencia.html')
