from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.rh import rh_service

def tela_colaboradores(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    perfil = request.session.get('perfil_usuario', 'Vendedor')
    login_usuario = request.session.get('usuario_logado')
    
    equipe, lojas = rh_service.obter_lista_equipe(perfil, login_usuario)
    return render(request, 'inventario/colaboradores.html', {'equipe': equipe, 'lojas': lojas})

def salvar_colaborador(request):
    if request.method == 'POST':
        try:
            msg = rh_service.salvar_membro_equipe(
                request.POST, 
                request.session.get('perfil_usuario', ''), 
                request.session.get('usuario_logado', '')
            )
            messages.success(request, msg)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erro inesperado ao salvar: {str(e)}")
    return redirect('tela_colaboradores')

def excluir_colaborador(request, id):
    if 'usuario_logado' not in request.session: return redirect('login')
    try:
        login = rh_service.excluir_membro_equipe(id, request.session.get('perfil_usuario', ''))
        messages.success(request, f"Colaborador '{login}' removido com sucesso!")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Erro ao excluir: {str(e)}")
    return redirect('tela_colaboradores')
