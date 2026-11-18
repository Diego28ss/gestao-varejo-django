from cryptography.fernet import Fernet
import base64
import hashlib
from django.conf import settings
from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages

# ==========================================
# 🚀 GRUPOS DE PERMISSÕES (CENTRALIZADOS)
# ==========================================
PERMISSOES_DEV = ['DEV']  
PERMISSOES_GERENCIA = ['GERENTE', 'DEV']
PERMISSOES_CAIXA = ['GERENTE', 'DEV', 'CAIXA']
PERMISSOES_ESTOQUE = ['GERENTE', 'DEV', 'ESTOQUISTA']
PERMISSOES_VENDAS = ['GERENTE', 'DEV', 'VENDEDOR', 'CAIXA']
PERMISSOES_TODOS = ['GERENTE', 'DEV', 'VENDEDOR', 'CAIXA', 'ESTOQUISTA']

# ==========================================
# 🚀 DECORADOR DE ACESSO (O GUARDA-COSTAS INTELIGENTE)
# ==========================================
def requer_perfil(perfis_permitidos):
    """
    Bloqueia a tela se o usuário não estiver logado 
    ou se não tiver um dos perfis listados (tratando maiúsculas/minúsculas).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Verifica se está logado
            if 'usuario_logado' not in request.session:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'sucesso': False, 'erro': 'Sessão expirada. Faça login novamente.'}, status=401)
                messages.error(request, "Sua sessão expirou. Faça login novamente.")
                return redirect('login')
            
            # 2. Recupera e normaliza o perfil da sessão (suporta 'perfil' ou 'perfil_usuario')
            perfil_usuario = request.session.get('perfil') or request.session.get('perfil_usuario')
            perfil_normalizado = str(perfil_usuario).strip().upper() if perfil_usuario else ''
            
            # Normaliza a lista de perfis permitidos para maiúsculo
            perfis_permitidos_upper = [str(p).strip().upper() for p in perfis_permitidos]

            if perfil_normalizado not in perfis_permitidos_upper:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'sucesso': False, 'erro': 'Acesso negado para o seu perfil.'}, status=403)
                
                messages.error(request, "Acesso restrito. Seu cargo não tem permissão para acessar esta tela.")
                return redirect('painel_principal')
            
            # 3. Tudo certo! Libera a execução da view original
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# ==========================================
# 🔐 SERVIÇO DE CRIPTOGRAFIA
# ==========================================
class SecurityService:
    @staticmethod
    def _get_fernet():
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @staticmethod
    def encrypt(value):
        if not value:
            return value
        f = SecurityService._get_fernet()
        return f.encrypt(str(value).encode()).decode()

    @staticmethod
    def decrypt(value):
        if not value:
            return value
        try:
            f = SecurityService._get_fernet()
            return f.decrypt(str(value).encode()).decode()
        except Exception:
            return value
        