from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.auth.auth_service import autenticar_usuario

def tela_login(request):
    """ View Fina: Controla apenas a sessão e o redirecionamento """
    if 'usuario_logado' in request.session:
        return redirect('painel_principal')

    if request.method == 'POST':
        login_input = request.POST.get('login', '').strip()
        senha_input = request.POST.get('senha', '').strip()

        try:
            # Chama o Cérebro para validar
            colaborador = autenticar_usuario(login_input, senha_input)
            
            if colaborador:
                request.session['usuario_logado'] = colaborador.login
                request.session['perfil_usuario'] = colaborador.perfil
                messages.success(request, f"Bem-vindo de volta, {colaborador.login}!")
                return redirect('painel_principal')
            else:
                messages.error(request, "Usuário ou senha incorretos.")

        except Exception as e:
            print(f"Erro crítico no login: {e}")
            messages.error(request, "Ocorreu um erro interno. Tente novamente.")

    return render(request, 'inventario/login.html')

def logout(request):
    """ Limpa a sessão com segurança """
    request.session.flush()
    return redirect('login')
