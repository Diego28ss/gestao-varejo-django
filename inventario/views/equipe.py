# inventario/views/equipe.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import json
from django.utils import timezone
from django.db.models import Sum

from inventario.models import Usuarios, Vendas

def tela_colaboradores(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    # REGRA: Vendedor ou Supervisor vê apenas a si mesmo na tabela
    perfil = request.session.get('perfil_usuario', 'Vendedor')
    login_usuario = request.session.get('usuario_logado')
    
    if perfil == 'Gerente':
        lista_equipe = Usuarios.objects.all()
    else:
        lista_equipe = Usuarios.objects.filter(login=login_usuario)
        
    agora = timezone.now()
    
    for colaborador in lista_equipe:
        vendas_do_vendedor = Vendas.objects.filter(
            vendedor=colaborador.login, 
            status='VENDA',
            data_venda__month=agora.month,
            data_venda__year=agora.year
        ).aggregate(
            total_vendido=Sum('valor_total'),
            comissao_total=Sum('valor_comissao') 
        )
        
        colaborador.total_vendido = vendas_do_vendedor['total_vendido'] or 0.00
        colaborador.comissao_a_pagar = vendas_do_vendedor['comissao_total'] or 0.00
        colaborador.escala_json_str = json.dumps(colaborador.escala_semanal) if colaborador.escala_semanal else "{}"
        
    return render(request, 'inventario/colaboradores.html', {'equipe': lista_equipe})

def salvar_colaborador(request):
    if request.method == 'POST':
        colaborador_id = request.POST.get('colaborador_id')
        login = request.POST.get('login', '').strip()
        senha_nova = request.POST.get('senha', '').strip()
        senha_conf = request.POST.get('senha_confirmacao', '').strip()
        perfil_post = request.POST.get('perfil', 'Colaborador')
        comissao = request.POST.get('comissao', '0.00').replace(',', '.')
        
        if senha_nova and senha_nova != senha_conf:
            messages.error(request, "As senhas não conferem. Alteração não realizada.")
            return redirect('tela_colaboradores')
        
        perfil_usuario_logado = request.session.get('perfil_usuario', '')
        
        escala_str = request.POST.get('escala_json', '{}')
        try:
            escala_semanal = json.loads(escala_str)
        except:
            escala_semanal = {}

        try:
            if colaborador_id and colaborador_id.strip() and colaborador_id != 'None':
                colaborador = get_object_or_404(Usuarios, id=colaborador_id)
                
                # Proteção: Vendedor não pode alterar login, comissão, perfil ou escala
                if perfil_usuario_logado != 'Gerente':
                    if request.session.get('usuario_logado') != colaborador.login:
                        messages.error(request, "Você não tem permissão para editar outros usuários.")
                        return redirect('tela_colaboradores')
                else:
                    if Usuarios.objects.filter(login=login).exclude(id=colaborador.id).exists():
                        messages.error(request, f"Erro: O login '{login}' já está em uso.")
                        return redirect('tela_colaboradores')
                    colaborador.login = login
                    colaborador.perfil = perfil_post
                    colaborador.comissao = comissao
                    colaborador.escala_semanal = escala_semanal

                if senha_nova:
                    colaborador.senha = senha_nova
                
                colaborador.save()
                messages.success(request, f"Colaborador '{colaborador.login}' atualizado com sucesso!")
            else:
                if perfil_usuario_logado != 'Gerente':
                    messages.error(request, "Apenas Gerentes podem criar novos usuários.")
                    return redirect('tela_colaboradores')
                    
                colaborador_existente = Usuarios.objects.filter(login=login).first()
                if colaborador_existente:
                    if senha_nova:
                        colaborador_existente.senha = senha_nova
                    colaborador_existente.perfil = perfil_post
                    colaborador_existente.comissao = comissao
                    colaborador_existente.escala_semanal = escala_semanal
                    colaborador_existente.save()
                    messages.success(request, f"Colaborador '{login}' atualizado.")
                else:
                    Usuarios.objects.create(
                        login=login, 
                        senha=senha_nova, 
                        perfil=perfil_post, 
                        comissao=comissao,
                        escala_semanal=escala_semanal
                    )
                    messages.success(request, f"Colaborador '{login}' cadastrado com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro inesperado ao salvar: {str(e)}")

    return redirect('tela_colaboradores')

def excluir_colaborador(request, id):
    if request.session.get('perfil_usuario') != 'Gerente':
        messages.error(request, "Apenas Gerentes podem excluir usuários.")
        return redirect('tela_colaboradores')
        
    colaborador = get_object_or_404(Usuarios, id=id)
    login = colaborador.login
    colaborador.delete()
    messages.success(request, f"Colaborador '{login}' removido com sucesso!")
    return redirect('tela_colaboradores')
