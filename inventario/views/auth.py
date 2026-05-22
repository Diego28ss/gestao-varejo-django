from django.shortcuts import render, redirect
from django.contrib import messages

# Como agora estamos dentro da pasta views, precisamos importar o model
# apontando para a pasta principal do app (inventario)
from inventario.models import Usuarios

# ==========================================
# 🔐 AUTENTICAÇÃO (LOGIN / LOGOUT)
# ==========================================

def tela_login(request):
    # Proteção: Se o usuário já estiver logado, manda direto para o painel principal
    if 'usuario_logado' in request.session:
        return redirect('painel_principal')

    if request.method == 'POST':
        login_input = request.POST.get('login', '').strip()
        senha_input = request.POST.get('senha', '').strip()

        try:
            # Busca o colaborador no banco de dados
            colaborador = Usuarios.objects.filter(login=login_input, senha=senha_input).first()

            if colaborador:
                # Registra as credenciais na sessão com segurança
                request.session['usuario_logado'] = colaborador.login
                request.session['perfil_usuario'] = colaborador.perfil

                messages.success(request, f"Bem-vindo de volta, {colaborador.login}!")
                return redirect('painel_principal')
            else:
                messages.error(request, "Usuário ou senha incorretos.")

        except Exception as e:
            print(f"Erro crítico no login: {e}")
            messages.error(request, "Ocorreu um erro interno ao tentar realizar o login. Tente novamente.")

    return render(request, 'inventario/login.html')


def logout(request):
    # Limpa toda a sessão do usuário com segurança
    request.session.flush()
    # Manda de volta para a tela de login
    return redirect('login')
