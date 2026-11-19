import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from inventario.services.security_service import requer_perfil, PERMISSOES_TODOS
from inventario.services.suporte import suporte_service

@require_POST
@requer_perfil(PERMISSOES_TODOS)
def api_chat_suporte(request):
    try:
        dados = json.loads(request.body.decode('utf-8'))
        pergunta = str(dados.get('pergunta', '')).strip()
        historico = dados.get('historico', [])

        if not pergunta:
            return JsonResponse({'sucesso': False, 'erro': 'Digite uma pergunta válida.'}, status=400)

        perfil = request.session.get('perfil') or request.session.get('perfil_usuario') or 'Vendedor'
        usuario = request.session.get('usuario_logado', '')

        resposta_ia = suporte_service.consultar_suporte_ia(
            pergunta=pergunta,
            historico=historico,
            perfil_usuario=perfil,
            nome_usuario=usuario
        )

        return JsonResponse({
            'sucesso': True,
            'resposta': resposta_ia
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': f'Erro interno no suporte: {str(e)}'}, status=500)
    