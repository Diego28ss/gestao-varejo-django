from django.shortcuts import render, redirect

# ==========================================
# 📊 PAINEL PRINCIPAL
# ==========================================

def painel_principal(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/index.html')
