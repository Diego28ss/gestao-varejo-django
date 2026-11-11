from cryptography.fernet import Fernet
import base64
import hashlib
from django.conf import settings

class SecurityService:
    @staticmethod
    def _get_fernet():
        # Deriva uma chave segura de 32 url-safe base64 bytes a partir da SECRET_KEY do Django
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
            # Caso o dado não esteja encriptado ou ocorra erro na chave, retorna o valor original
            return value
        