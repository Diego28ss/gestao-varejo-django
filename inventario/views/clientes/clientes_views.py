from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from inventario.models import Clientes, ConfiguracaoPontos
from inventario.services.clientes import clientes_service

# ==========================================
# GESTÃO DE CLIENTES E CRM
# ==========================================
def tela_consultar_clientes(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    query = request.GET.get('q', '')
    lista_clientes = clientes_service.processar_listagem_clientes(query)
    return render(request, 'inventario/consultar_clientes.html', {'clientes': lista_clientes, 'query': query})

def salvar_edicao_cliente(request):
    if request.method == 'POST':
        try:
            cliente = clientes_service.salvar_cliente(request.POST, request.POST.get('cliente_id'))
            messages.success(request, f"Ficha de {cliente.nome} salva com sucesso!")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erro interno: {str(e)}")
    return redirect('tela_consultar_clientes')

def api_historico_cliente(request, cliente_id=None):
    try:
        termo_busca = request.GET.get('nome', '').strip()
        dados = clientes_service.buscar_historico(cliente_id, termo_busca)
        return JsonResponse({'status': 'sucesso', 'historico': dados})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

def excluir_cliente(request, id):
    if 'usuario_logado' not in request.session: return redirect('login')
    try:
        Clientes.objects.get(id=id).delete()
    except Exception:
        pass
    return redirect('tela_consultar_clientes')

# ==========================================
# MANUTENÇÃO DE PONTOS / FIDELIDADE
# ==========================================
def tela_manutencao_pontos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') != 'Gerente':
        messages.error(request, "Acesso restrito exclusivamente ao cargo Gerente.")
        return redirect('painel_principal')
        
    return render(request, 'inventario/manutencao_pontos.html', {
        'conf_cliente': ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first(),
        'conf_pintor': ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
    })

def salvar_configuracao_pontos(request):
    if request.method == 'POST':
        try:
            clientes_service.atualizar_regras_fidelidade(
                request.POST.get('acumulo_cliente', 1),
                request.POST.get('acumulo_pintor', 1)
            )
            messages.success(request, "Regras de Fidelidade atualizadas com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro: {str(e)}")
    return redirect('tela_manutencao_pontos')
