import json
from pathlib import Path
from django.conf import settings
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import render
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

        # Detecta automaticamente se a IA informou que não encontrou no manual
        frases_sem_resposta = [
            'não encontrei no manual',
            'não está documentado',
            'procure o gerente',
            'não tenho essa informação',
            'erro na ia:'
        ]
        nao_soube = any(f in resposta_ia.lower() for f in frases_sem_resposta)

        log = LogSuporteIA.objects.create(
            usuario=usuario,
            perfil=perfil,
            rota_origem=rota_atual,
            pergunta=pergunta,
            resposta=resposta_ia,
            usou_ferramenta_banco=usou_ferramenta,
            feedback='NAO_AJUDOU' if nao_soube else 'PENDENTE'
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
        voto = str(dados.get('voto', '')).strip().upper()

        if not log_id or voto not in ['UTIL', 'NAO_AJUDOU']:
            return JsonResponse({'sucesso': False, 'erro': 'Dados de feedback inválidos.'}, status=400)

        LogSuporteIA.objects.filter(id=log_id).update(feedback=voto)
        return JsonResponse({'sucesso': True})

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@requer_perfil(['Gerente', 'DEV'])
def tela_aprendizado_ia(request):
    """Painel de Gerência com Ranking das dúvidas não respondidas / 👎 por quantidade."""
    total_perguntas = LogSuporteIA.objects.count()
    total_uteis = LogSuporteIA.objects.filter(feedback='UTIL').count()
    total_ruins = LogSuporteIA.objects.filter(feedback='NAO_AJUDOU', resolvido_manual=False).count()

    avaliados = total_uteis + LogSuporteIA.objects.filter(feedback='NAO_AJUDOU').count()
    taxa_aprovacao = round((total_uteis / avaliados) * 100) if avaliados > 0 else 100

    # Ranking das dúvidas não respondidas / 👎 ordenadas da mais frequente para a menos frequente
    ranking_nao_respondidas = (
        LogSuporteIA.objects
        .filter(feedback='NAO_AJUDOU', resolvido_manual=False)
        .values('pergunta_normalizada')
        .annotate(
            quantidade=Count('id'),
            exemplo_pergunta=Max('pergunta'),
            ultima_resposta=Max('resposta'),
            rota_mais_comum=Max('rota_origem'),
            ultima_data=Max('data_hora')
        )
        .order_by('-quantidade', '-ultima_data')
    )

    # Top 10 dúvidas mais perguntadas no geral pela equipe
    top_geral = (
        LogSuporteIA.objects
        .values('pergunta_normalizada')
        .annotate(
            quantidade=Count('id'),
            exemplo_pergunta=Max('pergunta'),
            rota_mais_comum=Max('rota_origem')
        )
        .order_by('-quantidade')[:10]
    )

    contexto = {
        'total_perguntas': total_perguntas,
        'total_uteis': total_uteis,
        'total_ruins': total_ruins,
        'taxa_aprovacao': taxa_aprovacao,
        'ranking_nao_respondidas': ranking_nao_respondidas,
        'top_geral': top_geral,
    }
    return render(request, 'inventario/aprendizado_ia.html', contexto)


@require_POST
@requer_perfil(['Gerente', 'DEV'])
def api_ensinar_ia(request):
    """Grava uma nova solução no manual_tecvarejo.md, limpa o cache da IA e marca como resolvida."""
    try:
        dados = json.loads(request.body.decode('utf-8'))
        pergunta_norm = str(dados.get('pergunta_normalizada', '')).strip()
        pergunta_titulo = str(dados.get('pergunta_titulo', '')).strip()
        resposta_oficial = str(dados.get('resposta_oficial', '')).strip()
        acao = str(dados.get('acao', 'ENSINAR')).strip().upper()

        if not pergunta_norm:
            return JsonResponse({'sucesso': False, 'erro': 'Identificador da pergunta inválido.'}, status=400)

        if acao == 'ARQUIVAR':
            LogSuporteIA.objects.filter(pergunta_normalizada=pergunta_norm).update(resolvido_manual=True)
            return JsonResponse({'sucesso': True, 'mensagem': 'Dúvida arquivada com sucesso!'})

        if not pergunta_titulo or not resposta_oficial:
            return JsonResponse({'sucesso': False, 'erro': 'Preencha a pergunta e a resposta oficial.'}, status=400)

        caminho_manual = Path(settings.BASE_DIR) / 'inventario' / 'docs' / 'manual_tecvarejo.md'
        novo_bloco = f'\n- **"{pergunta_titulo}":** {resposta_oficial}\n'

        with open(caminho_manual, 'a', encoding='utf-8') as f:
            f.write(novo_bloco)

        # Limpa o cache em memória para a IA aprender imediatamente na próxima pergunta
        suporte_service._CACHE_MANUAL = None

        LogSuporteIA.objects.filter(pergunta_normalizada=pergunta_norm).update(resolvido_manual=True)

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Regra salva no manual! A IA já aprendeu essa resposta.'
        })

    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': f'Erro ao salvar no manual: {str(e)}'}, status=500)
    