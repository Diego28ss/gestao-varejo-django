import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from inventario.services.security_service import requer_perfil, PERMISSOES_TODOS
from inventario.services.suporte import suporte_service
from inventario.models import LogSuporteIA


@require_POST
@requer_perfil(PERMISSOES_TODOS)
def api_chat_suporte(request):
    try:
        dados = json.loads(request.body.decode('utf-8'))
        pergunta = str(dados.get('pergunta', '')).strip()
        historico = dados.get('historico', [])
        rota_atual = str(dados.get('rota_atual', '/')).strip()

        if not pergunta:
            return JsonResponse({'sucesso': False, 'erro': 'Digite uma pergunta válida.'}, status=400)

        perfil = request.session.get('perfil') or request.session.get('perfil_usuario') or 'Vendedor'
        usuario = request.session.get('usuario_logado', '')

        resultado = suporte_service.consultar_suporte_ia(
            pergunta=pergunta,
            historico=historico,
            perfil_usuario=perfil,
            nome_usuario=usuario,
            rota_atual=rota_atual
        )

        resposta_ia = resultado['resposta']
        usou_ferramenta = resultado['usou_ferramenta']

        # Grava silenciosamente no log para aprendizado contínuo
        log = LogSuporteIA.objects.create(
            usuario=usuario,
            perfil=perfil,
            rota_origem=rota_atual,
            pergunta=pergunta,
            resposta=resposta_ia,
            usou_ferramenta_banco=usou_ferramenta
        )

        return JsonResponse({
            'sucesso': True,
            'resposta': resposta_ia,
            'log_id': log.id
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': f'Erro interno no suporte: {str(e)}'}, status=500)


@require_POST
@requer_perfil(PERMISSOES_TODOS)
def api_feedback_suporte(request):
    try:
        dados = json.loads(request.body.decode('utf-8'))
        log_id = dados.get('log_id')
        voto = str(dados.get('voto', '')).strip().upper()  # 'UTIL' ou 'NAO_AJUDOU'

        if not log_id or voto not in ['UTIL', 'NAO_AJUDOU']:
            return JsonResponse({'sucesso': False, 'erro': 'Dados de feedback inválidos.'}, status=400)

        LogSuporteIA.objects.filter(id=log_id).update(feedback=voto)
        return JsonResponse({'sucesso': True})

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)
    