from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.rh import rh_service

def tela_ponto(request):
    return render(request, 'inventario/bater_ponto.html')

def registrar_batida(request):
    if request.method == 'POST':
        try:
            status, msg = rh_service.registrar_ponto(
                request.POST.get('username', '').strip(),
                request.POST.get('password', '').strip()
            )
            if status in ["DEV", "ESGOTADO"]:
                messages.warning(request, msg)
            else:
                messages.success(request, msg)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erro interno: {str(e)}")
    return redirect('tela_ponto')
