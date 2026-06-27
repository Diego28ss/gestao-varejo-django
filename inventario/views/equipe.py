from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import json  # Importante para processar a escala vinda do HTML

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
        
        # 🔥 CORREÇÃO AQUI: Traduz o Python Dict para um JSON perfeito para o navegador ler
        colaborador.escala_json_str = json.dumps(colaborador.escala_semanal) if colaborador.escala_semanal else "{}"

    return render(request, 'inventario/colaboradores.html', {'equipe': lista_equipe})


def salvar_colaborador(request):
    if request.method == 'POST':
        colaborador_id = request.POST.get('colaborador_id')
        login = request.POST.get('login', '').strip()
        senha_nova = request.POST.get('senha', '').strip()
        perfil = request.POST.get('perfil', 'Colaborador')
        comissao = request.POST.get('comissao', '0.00').replace(',', '.')
        
        # Captura o pacote JSON com todos os dias da semana construído no Front-End
        escala_str = request.POST.get('escala_json', '{}')
        try:
            escala_semanal = json.loads(escala_str)
        except:
            escala_semanal = {}

        try:
            if colaborador_id and colaborador_id.strip() and colaborador_id != 'None':
                colaborador = get_object_or_404(Usuarios, id=colaborador_id)

                if Usuarios.objects.filter(login=login).exclude(id=colaborador.id).exists():
                    messages.error(request, f"Erro: O login '{login}' já está em uso por outra pessoa!")
                    return redirect('tela_colaboradores')

                colaborador.login = login

                if senha_nova:
                    colaborador.senha = senha_nova

                colaborador.perfil = perfil
                colaborador.comissao = comissao
                
                # Atribuição da nova estrutura JSON
                colaborador.escala_semanal = escala_semanal
                
                colaborador.save()
                messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")

            else:
                colaborador_existente = Usuarios.objects.filter(login=login).first()
                if colaborador_existente:
                    if senha_nova:
                        colaborador_existente.senha = senha_nova

                    colaborador_existente.perfil = perfil
                    colaborador_existente.comissao = comissao
                    
                    # Atribuição da nova estrutura JSON (Edição)
                    colaborador_existente.escala_semanal = escala_semanal
                    
                    colaborador_existente.save()
                    messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")
                else:
                    # Criação de um novo colaborador com a escala JSON
                    Usuarios.objects.create(
                        login=login, 
                        senha=senha_nova, 
                        perfil=perfil, 
                        comissao=comissao,
                        escala_semanal=escala_semanal
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
