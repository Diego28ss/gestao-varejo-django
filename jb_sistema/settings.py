import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 🌟 CORREÇÃO 1: Aponta o radar diretamente para a raiz do projeto onde está o .env
load_dotenv(BASE_DIR / '.env')

# A chave secreta agora vem do cofre. Se falhar, usa uma de emergência.
SECRET_KEY = os.getenv("SECRET_KEY", "chave-de-emergencia-insegura")

# 🌟 CORREÇÃO 2: Força o padrão para True se ele não achar o cofre, e remove espaços invisíveis
DEBUG = str(os.getenv("DEBUG", "True")).strip().lower() == "true"

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventario',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        # Puxa o nome do banco de dados do cofre
        'NAME': BASE_DIR / os.getenv("DB_NAME", "jb_tintas.db"), 
    },
    'tintometrico_db': {  # <--- COLOQUE O "_db" AQUI!
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv("DB_TINTOMETRICO", "banco_tintometrico.db"), 
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
ROOT_URLCONF = 'jb_sistema.urls'
WSGI_APPLICATION = 'jb_sistema.wsgi.application'

# TEM QUE TER A BARRA NO INÍCIO E NO FIM
STATIC_URL = '/static/'  

# Faz o Django enxergar a pasta static na raiz do projeto
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'
DATABASE_ROUTERS = ['jb_sistema.db_router.TintometricoRouter']
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
