from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

# Importação dos modelos necessários para gestão da equipe e cálculo de comissões
from inventario.models import Usuarios, Vendas

# ==========================================
# 👥 GESTÃO DE EQUIPE E COMISSÕES
# ==========================================

def tela_colaboradores(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    lista_equipe = Usuarios.objects.all()

    for colaborador in lista_equipe:
        # Busca todas as vendas finalizadas deste vendedor específico
        vendas_do_vendedor = Vendas.objects.filter(vendedor=colaborador.login, status='VENDA')

        total_vendido = 0.0
        for v in vendas_do_vendedor:
            try:
                total_vendido += float(v.valor_total)
            except (ValueError, TypeError):
                pass

        try:
            percentual_comissao = float(colaborador.comissao)
        except (ValueError, TypeError):
            percentual_comissao = 0.0

        comissao_a_pagar = (total_vendido * percentual_comissao) / 100

        colaborador.total_vendido = total_vendido
        colaborador.comissao_a_pagar = comissao_a_pagar

    context = {
        'equipe': lista_equipe,
    }
    return render(request, 'inventario/colaboradores.html', context)


def salvar_colaborador(request):
    if request.method == 'POST':
        colaborador_id = request.POST.get('colaborador_id')
        login = request.POST.get('login', '').strip()
        senha_nova = request.POST.get('senha', '').strip()
        perfil = request.POST.get('perfil', 'Colaborador')
        comissao = request.POST.get('comissao', '0.00').replace(',', '.')
        
        # Captura os novos campos de horário
        h_entrada = request.POST.get('h_entrada') or None
        t_almoco = request.POST.get('t_almoco') or None
        h_saida = request.POST.get('h_saida') or None

        try:
            if colaborador_id and colaborador_id.strip() and colaborador_id != 'None':
                colaborador = get_object_or_404(Usuarios, id=colaborador_id)

                if Usuarios.objects.filter(login=login).exclude(id=colaborador.id).exists():
                    messages.error(request, f"Erro: O login '{login}' já está em uso!")
                    return redirect('tela_colaboradores')

                colaborador.login = login
                if senha_nova:
                    colaborador.senha = senha_nova
                colaborador.perfil = perfil
                colaborador.comissao = comissao
                
                # ATRIBUIÇÃO DOS HORÁRIOS (Edição)
                colaborador.H_entrada = h_entrada
                colaborador.T_almoco = t_almoco
                colaborador.H_saida = h_saida
                
                colaborador.save()
                messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")

            else:
                colaborador_existente = Usuarios.objects.filter(login=login).first()
                if colaborador_existente:
                    if senha_nova:
                        colaborador_existente.senha = senha_nova
                    colaborador_existente.perfil = perfil
                    colaborador_existente.comissao = comissao
                    
                    # ATRIBUIÇÃO DOS HORÁRIOS (Edição caso já exista)
                    colaborador_existente.H_entrada = h_entrada
                    colaborador_existente.T_almoco = t_almoco
                    colaborador_existente.H_saida = h_saida
                    
                    colaborador_existente.save()
                    messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")
                else:
                    # ATRIBUIÇÃO DOS HORÁRIOS (Novo Cadastro)
                    Usuarios.objects.create(
                        login=login, senha=senha_nova, perfil=perfil, comissao=comissao,
                        H_entrada=h_entrada, T_almoco=t_almoco, H_saida=h_saida
                    )
                    messages.success(request, f"Colaborador '{login}' cadastrado com sucesso!")

        except Exception as e:
            messages.error(request, f"Erro inesperado ao salvar: {str(e)}")

    return redirect('tela_colaboradores')


def excluir_colaborador(request, id):
    colaborador = get_object_or_404(Usuarios, id=id)
    login = colaborador.login
    colaborador.delete()
    messages.success(request, f"Colaborador '{login}' removido com sucesso!")
    return redirect('tela_colaboradores')
