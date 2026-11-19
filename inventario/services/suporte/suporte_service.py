import os
import traceback
from pathlib import Path
from django.conf import settings
from google import genai
from google.genai import types

CAMINHO_MANUAL = Path(settings.BASE_DIR) / 'inventario' / 'docs' / 'manual_tecvarejo.md'

# Cache em memória para leitura instantânea do manual
_CACHE_MANUAL = None

# Modelos validados na sua chave de API
MODELOS_SUPORTE = [
    'gemini-3.8-flash',
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash-lite',
]

def carregar_manual_sistema():
    """Lê o arquivo manual_tecvarejo.md com cache em memória."""
    global _CACHE_MANUAL
    if _CACHE_MANUAL is not None:
        return _CACHE_MANUAL

    try:
        if CAMINHO_MANUAL.exists():
            _CACHE_MANUAL = CAMINHO_MANUAL.read_text(encoding='utf-8')
            return _CACHE_MANUAL
        return "Manual do sistema não encontrado."
    except Exception as e:
        return f"Erro ao carregar manual: {str(e)}"

def consultar_suporte_ia(pergunta: str, historico: list = None, perfil_usuario: str = 'Vendedor', nome_usuario: str = '') -> str:
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        return "⚠️ A chave da API do Gemini (GEMINI_API_KEY) não está configurada no arquivo .env do servidor."

    manual_texto = carregar_manual_sistema()

    instrucao_mestre = f"""
Você é o **Suporte Inteligente do TecVarejo**, um colega experiente, simpático e muito didático que ajuda a equipe da loja no dia a dia.

BASE DE CONHECIMENTO OFICIAL DO SISTEMA:
{manual_texto}

---
CONTEXTO DO USUÁRIO LOGADO AGORA:
- Nome/Login: {nome_usuario or 'Colaborador'}
- Perfil de acesso: {perfil_usuario}

COMO VOCÊ DEVE CONVERSAR (MUITO IMPORTANTE):
1. **Seja Humano, Leve e Didático:** Fale de forma natural, acolhedora e simples, como um colega de trabalho explicando no balcão. Evite textos longos e robóticos.
2. **Pergunte Antes Quando Houver Mais de Uma Opção (Regra de Clareza):**
   - Se o usuário perguntar algo amplo que tem dois caminhos no sistema, NÃO despeje tudo de uma vez! Faça uma pergunta curta e amigável primeiro para entender o que ele precisa:
     * Exemplo ("Como emitir nota fiscal?"): Pergunte se ele deseja emitir uma **NFC-e (Cupom Fiscal de balcão)** ou uma **NF-e (Nota Fiscal grande em folha A4)**.
     * Exemplo ("Como ajustar/contar o estoque?"): Pergunte se ele quer fazer um **Acerto Rápido** de um produto avulso ou abrir um **Inventário Rotativo** de uma marca/família.
     * Exemplo ("Como cancelar uma venda ou pedido?"): Pergunte se o pedido ainda está **em aberto/aguardando caixa** ou se a venda já foi **faturada**.
   - Assim que ele responder na mensagem seguinte, aí sim dê o passo a passo exato!
3. **Links Clicáveis:** Sempre que citar uma tela, escreva a rota exata começando com barra (ex: `/clientes/`), pois o chat transforma isso em um botão clicável para o usuário.
4. **Permissões:** Se o recurso exigir perfil **Gerente** ou **Supervisor** e o usuário atual for `{perfil_usuario}` (diferente disso), explique com simpatia que ele precisará pedir a autorização do gerente/supervisor na tela.
5. **Fidelidade:** Nunca invente botões ou telas que não existam na base de conhecimento acima.
"""

    client = genai.Client(api_key=api_key)

    conteudos = []
    if historico and isinstance(historico, list):
        for msg in historico[-8:]:
            role = 'user' if msg.get('autor') == 'usuario' else 'model'
            texto = str(msg.get('texto', '')).strip()
            if texto:
                conteudos.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=texto)]
                    )
                )

    conteudos.append(
        types.Content(
            role='user',
            parts=[types.Part.from_text(text=pergunta)]
        )
    )

    ultimo_erro = ""
    for modelo in MODELOS_SUPORTE:
        try:
            print(f"[DEBUG SUPORTE IA] Tentando modelo: {modelo}")
            resposta = client.models.generate_content(
                model=modelo,
                contents=conteudos,
                config=types.GenerateContentConfig(
                    system_instruction=instrucao_mestre,
                    temperature=0.35,
                )
            )
            print(f"[DEBUG SUPORTE IA] Sucesso com: {modelo}")
            return resposta.text or "Não consegui formular uma resposta agora. Pode repetir de outro jeito?"

        except Exception as e:
            ultimo_erro = str(e)
            print(f"[DEBUG SUPORTE IA] Falha no modelo '{modelo}': {ultimo_erro}")
            if any(codigo in ultimo_erro for codigo in ['404', 'NOT_FOUND', '503', 'UNAVAILABLE', '429', 'RESOURCE_EXHAUSTED']):
                continue
            traceback.print_exc()
            break

    return f"⚠️ Erro na IA: {ultimo_erro}"
