from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from inventario.models.banco_rh import PontoEletronico
from inventario.models.pessoas import Usuarios

def tela_ponto(request):
    return render(request, 'inventario/bater_ponto.html')

def registrar_batida(request):
    if request.method == 'POST':
        usuario_digitado = request.POST.get('username', '').strip()
        senha_digitada = request.POST.get('password', '').strip()
        
        # O sistema verifica o login/senha no banco principal (jb_tintas.db)
        user = Usuarios.objects.filter(login__exact=usuario_digitado, senha__exact=senha_digitada).first()
        
        if user is not None:
            agora = timezone.localtime()
            hoje = agora.date()
            hora_atual = agora.time()

            # O sistema guarda apenas o "nome" no banco do RH (banco_rh.db), sem forçar união de tabelas
            ponto, created = PontoEletronico.objects.get_or_create(colaborador_login=user.login, data=hoje)

            if not ponto.entrada_1:
                ponto.entrada_1 = hora_atual
                msg = "Entrada"
            elif not ponto.saida_1:
                ponto.saida_1 = hora_atual
                msg = "Saída para almoço"
            elif not ponto.entrada_2:
                ponto.entrada_2 = hora_atual
                msg = "Retorno do almoço"
            elif not ponto.saida_2:
                ponto.saida_2 = hora_atual
                msg = "Fim de expediente"
            else:
                messages.warning(request, f"{user.login.upper()}, a sua jornada de hoje já foi concluída.")
                return redirect('tela_ponto')

            ponto.save()
            messages.success(request, f"{msg} registada para {user.login.upper()} às {hora_atual.strftime('%H:%M')}!")
        else:
            messages.error(request, "Utilizador ou senha incorretos. Verifique se o login está exatamente como cadastrado.")
            
    return redirect('tela_ponto')
