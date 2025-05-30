# config/settings/development.py

import sys
from .base import *

# === DESENVOLVIMENTO ===

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# === APPS ADICIONAIS PARA DEV ===
# django_extensions já está em base.py

# Debug Toolbar apenas se disponível
try:
    import debug_toolbar

    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

    # Configuração do Debug Toolbar
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        'SHOW_COLLAPSED': True,
    }

    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]

except ImportError:
    pass

# === BANCO DE DADOS ===

# PostgreSQL por padrão (mesmo do production)
# Usar DATABASE_URL se fornecida, senão usar variáveis individuais
if env('DATABASE_URL', default=None):
    import dj_database_url

    DATABASES['default'] = dj_database_url.parse(env('DATABASE_URL'), conn_max_age=600)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='vortex_board'),
            'USER': env('DB_USER', default='vortex_user'),
            'PASSWORD': env('DB_PASSWORD', default='vortex123'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
            'OPTIONS': {
                'sslmode': 'prefer',  # Mais flexível que 'require'
            },
            'CONN_MAX_AGE': 60,  # Conexões persistentes
        }
    }

# Fallback para SQLite apenas se explicitamente solicitado
if env('USE_SQLITE', cast=bool, default=False):
    print("🔄 Usando SQLite para desenvolvimento")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    print(f"🐘 Usando PostgreSQL: {DATABASES['default']['NAME']}@{DATABASES['default']['HOST']}")

# Configuração específica para desenvolvimento
DATABASES['default']['ATOMIC_REQUESTS'] = True  # Transações automáticas

# === EMAIL ===

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# === LOGGING MAIS VERBOSO ===

LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG'

LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# === CONFIGURAÇÕES DE DESENVOLVIMENTO ===

# Cache simples em desenvolvimento (sem Redis obrigatório)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'vortex-dev-cache',
    }
}

# Usar Redis se disponível
if env('REDIS_URL', default=None):
    try:
        import redis

        # Testar conexão Redis
        r = redis.from_url(env('REDIS_URL'))
        r.ping()

        CACHES['default'] = {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': env('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
        print("🔴 Redis conectado com sucesso!")
    except Exception as e:
        print(f"⚠️  Redis não disponível: {e}")
        print("📝 Usando cache em memória local")

# Channels simplificado para desenvolvimento
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Permitir CORS para desenvolvimento frontend
CORS_ALLOW_ALL_ORIGINS = True

# Configurações mais relaxadas para desenvolvimento
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Configurações do shell_plus
SHELL_PLUS_IMPORTS = [
    'from apps.core.models import *',
    'from apps.core.utils import *',
    'from django.contrib.auth import get_user_model',
    'User = get_user_model()',
]

# Configurações para testes
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }

    # Desabilitar logs em testes
    LOGGING['handlers'] = {}
    LOGGING['loggers'] = {}

# === DJANGO EXTENSIONS ===

# Configurações do runserver_plus (se disponível)
try:
    import werkzeug

    RUNSERVER_PLUS_EXTRA_FILES = [
        BASE_DIR / 'static',
        BASE_DIR / 'templates',
    ]
except ImportError:
    pass

print("🚀 Configurações de DESENVOLVIMENTO carregadas")
print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"🔑 DEBUG: {DEBUG}")
print(f"🌐 ALLOWED_HOSTS: {ALLOWED_HOSTS}")