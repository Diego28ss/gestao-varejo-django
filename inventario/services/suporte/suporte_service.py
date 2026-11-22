import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
from django.conf import settings
from google import genai
from google.genai import types

from .ferramentas_ia import (
    consultar_estoque_produto,
    consultar_pontos_cliente,
    diagnosticar_nota_fiscal,
    listar_duvidas_nao_resolvidas,
)

CAMINHO_MANUAL = Path(settings.BASE_DIR) / 'inventario' / 'docs' / 'manual_tecvarejo.md'
CAMINHO_ENV = Path(settings.BASE_DIR) / '.env'

_CACHE_MANUAL = None
_CACHE_MANUAL_MTIME = 0

MODELOS_SUPORTE = [
    'gemini-3.5-flash-lite',          # 1º: 15 RPM | 250k TPM | 500 RPD
    'gemini-3.8-flash-lite',          # 2º: Estepe 1
    'gemini-3.8-flash',               # 3º: Estepe 2 (indicado pela API)
    'gemini-3.1-flash-lite-preview',  # 4º: Estepe 3
]


def carregar_manual_sistema():
    global _CACHE_MANUAL, _CACHE_MANUAL_MTIME

    try:
        if CAMINHO_MANUAL.exists():
            mtime_atual = CAMINHO_MANUAL.stat().st_mtime
            if _CACHE_MANUAL is not None and mtime_atual == _CACHE_MANUAL_MTIME:
                return _CACHE_MANUAL

            _CACHE_MANUAL = CAMINHO_MANUAL.read_text(encoding='utf-8')
            _CACHE_MANUAL_MTIME = mtime_atual
            return _CACHE_MANUAL
        return "Manual do sistema não encontrado."
    except Exception as e:
        return f"Erro ao carregar manual: {str(e)}"


def consultar_suporte_ia(
    pergunta: str,
    historico: list = None,
    perfil_usuario: str = 'Vendedor',
    nome_usuario: str = '',
    rota_atual: str = '/'
) -> dict:
    """
    Retorna um dicionário:
    {'resposta': str, 'usou_ferramenta': bool}
    """
    if CAMINHO_ENV.exists():
        load_dotenv(CAMINHO_ENV, override=True)

    api_key = os.getenv('GEMINI_API_KEY', '').strip() or getattr(settings, 'GEMINI_API_KEY', '').strip()
    if not api_key:
        return {
            'resposta': "⚠️ A chave da API do Gemini (GEMINI_API_KEY) não está configurada no arquivo .env do servidor.",
            'usou_ferramenta': False
        }

    manual_texto = carregar_manual_sistema()

    instrucao_mestre = f"""
Você é o **Suporte Inteligente do TecVarejo**, um colega experiente, simpático e muito didático que ajuda a equipe da loja no dia a dia.

BASE DE CONHECIMENTO OFICIAL DO SISTEMA (MANUAL + ERROS SEFAZ + REGRAS DA LOJA):
{manual_texto}

---
CONTEXTO DO USUÁRIO LOGADO AGORA:
- Nome/Login: {nome_usuario or 'Colaborador'}
- Perfil de acesso: {perfil_usuario}
- Tela que ele está olhando neste exato momento: `{rota_atual}`

COMO VOCÊ DEVE AGIR (MUITO IMPORTANTE):
1. **Seja Humano, Leve e Didático:** Fale de forma natural, acolhedora e simples, como um colega de trabalho explicando no balcão.
2. **Use as Ferramentas de Consulta ao Banco (Function Calling) Sempre que Necessário:**
  - Se o usuário perguntar sobre **estoque, preço ou corredor/local** de um produto -> chame `consultar_estoque_produto`.
  - Se perguntar sobre **pontos de fidelidade** de um cliente -> chame `consultar_pontos_cliente`.
  - Se perguntar **por que uma nota fiscal deu erro/rejeição** (ou pedir para checar uma venda) -> chame `diagnosticar_nota_fiscal`, leia o motivo do erro retornado, traduza em linguagem simples usando o Dicionário de Erros da SEFAZ do manual e diga exatamente o que ele precisa corrigir!
  - Se um Gerente ou DEV pedir as **dúvidas que receberam avaliação negativa** -> chame `listar_duvidas_nao_resolvidas`.
3. **Seja Direto Quando o Usuário Já Especificou o Recurso (Não Enrole):**
  - Se o usuário já especificou o que quer (ex: **"como emitir NF-e"**, **"como emitir NFC-e"**, **"acerto rápido"** ou **"inventário"**), **entregue o passo a passo completo imediatamente** com as rotas clicáveis e os nomes exatos dos botões e campos, sem fazer perguntas de confirmação!
  - Só pergunte antes se o pedido for realmente genérico e ambíguo (ex: *"como emitir nota fiscal?"* sem dizer se é NF-e ou NFC-e, ou *"como ajustar estoque?"* sem especificar o método).
4. **Guia Visual Interativo (Highlight na Tela):**
  - Se o usuário perguntar *"Onde fica o botão..."* ou *"Onde clico para..."* sobre um botão que existe na tela atual (`{rota_atual}`), inclua no final da sua resposta a tag exata: `[[DESTACAR:Texto do Botão]]` (ex: `[[DESTACAR:Sangria]]`, `[[DESTACAR:NOVO CADASTRO]]`, `[[DESTACAR:Acerto Rápido]]`, `[[DESTACAR:VENDA]]`, `[[DESTACAR:ORÇAMENTO]]`). O sistema fará o botão piscar na tela do usuário!
5. **Links Clicáveis:** Sempre que citar uma tela, escreva a rota exata começando com barra (ex: `/clientes/`), pois o chat transforma isso em um link clicável.
6. **Permissões:** Se o recurso exigir perfil **Gerente** ou **Supervisor** e o usuário for `{perfil_usuario}`, explique com simpatia que precisa da autorização do gerente/supervisor.
"""

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=15000)
    )

    ferramentas_disponiveis = [
        consultar_estoque_produto,
        consultar_pontos_cliente,
        diagnosticar_nota_fiscal,
        listar_duvidas_nao_resolvidas,
    ]

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
            resposta = client.models.generate_content(
                model=modelo,
                contents=conteudos,
                config=types.GenerateContentConfig(
                    system_instruction=instrucao_mestre,
                    temperature=0.35,
                    tools=ferramentas_disponiveis,
                )
            )
            usou_tool = bool(
                resposta.automatic_function_calling_history
                and len(resposta.automatic_function_calling_history) > 0
            )
            texto_final = resposta.text or "Não consegui formular uma resposta agora. Pode repetir de outro jeito?"
            return {
                'resposta': texto_final,
                'usou_ferramenta': usou_tool
            }

        except Exception as e:
            ultimo_erro = str(e)
            print(f"[DEBUG SUPORTE IA] Falha no modelo '{modelo}': {ultimo_erro}")
            if any(codigo in ultimo_erro.lower() for codigo in ['404', 'not_found', '503', 'unavailable', '429', 'resource_exhausted', 'timeout', 'timed out', 'deadline']):
                continue
            traceback.print_exc()
            break

    return {
        'resposta': f"⚠️ Erro na IA: {ultimo_erro}",
        'usou_ferramenta': False
    }
