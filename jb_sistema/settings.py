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
CSRF_TRUSTED_ORIGINS = ['https://varejoboost.up.railway.app']


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
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Garante o envio eficiente de CSS/JS na nuvem
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

# Configuração dos bancos de dados SQLite apontando para o volume estável
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv('DB_NAME', 'dados/jb_tintas.db'),
    },
    'tintometrico_db': {  
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv("DB_TINTOMETRICO", "dados/banco_tintometrico.db"), 
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
ROOT_URLCONF = 'jb_sistema.urls'
WSGI_APPLICATION = 'jb_sistema.wsgi.application'

# Configurações de Arquivos Estáticos (CSS, JS, Imagens do sistema)
STATIC_URL = '/static/'  
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Ativa a compressão e cache do WhiteNoise para os arquivos de design
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configurações de Mídia (Uploads de fotos/arquivos dos usuários)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')

DATABASE_ROUTERS = ['jb_sistema.db_router.TintometricoRouter']
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
