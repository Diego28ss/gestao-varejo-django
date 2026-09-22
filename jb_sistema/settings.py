import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Aponta o radar diretamente para a raiz do projeto onde está o .env
load_dotenv(BASE_DIR / '.env')

# A chave secreta vem do cofre do Railway. Se falhar, usa uma de emergência.
SECRET_KEY = os.getenv("SECRET_KEY", "chave-de-emergencia-insegura")

# Força o padrão para True se não achar a variável, removendo espaços invisíveis
DEBUG = str(os.getenv("DEBUG", "True")).strip().lower() == "true"

ALLOWED_HOSTS = ['*']

# Permissões de envio de formulários e APIs
CSRF_TRUSTED_ORIGINS = [
    'https://varejoboost.up.railway.app',
    'https://*.pythonanywhere.com'
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventario',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'dados' / 'jb_tintas.db', 
    },
    'tintometrico_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'dados' / 'banco_tintometrico.db',
    },
    'rh_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'dados' / 'banco_rh.db', 
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
ROOT_URLCONF = 'jb_sistema.urls'
WSGI_APPLICATION = 'jb_sistema.wsgi.application'

STATIC_URL = '/static/'  
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')
DATABASE_ROUTERS = ['jb_sistema.db_router.TintometricoRouter']
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
LOGIN_URL = 'login'

# ==========================================
# INTEGRAÇÃO FISCAL E CRIPTOGRAFIA MESTRA
# ==========================================
NOTAAS_API_KEY = os.getenv('NOTAAS_API_KEY', '')
NFE_AMBIENTE = int(os.getenv('NFE_AMBIENTE', 2))

# 🚀 NOVA CHAVE MESTRA: Esta chave criptografa e descriptografa o banco de dados.
# Adicione CRYPTOGRAPHY_KEY=sua-chave-aqui no seu arquivo .env no PythonAnywhere!
CRYPTOGRAPHY_KEY = os.getenv('CRYPTOGRAPHY_KEY', 'chave-criptografia-emergencia-muito-secreta-!')

# ==========================================
# 🔐 CONFIGURAÇÕES DE SEGURANÇA E SESSÃO (HARDENING)
# ==========================================
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 28800 
SESSION_COOKIE_SAMESITE = 'Lax'

# Impede o roubo de sessão caso o acesso não seja HTTPS em Produção
SESSION_COOKIE_SECURE = not DEBUG 
# Protege cookies contra roubo via JavaScript (XSS)
SESSION_COOKIE_HTTPONLY = True
# Impede que o navegador tente adivinhar a extensão de arquivos mascarados
SECURE_CONTENT_TYPE_NOSNIFF = True
# Proteção contra sequestro de cliques (iFrames de terceiros)
X_FRAME_OPTIONS = 'DENY'
