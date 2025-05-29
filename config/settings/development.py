# config/settings/development.py

import sys
from .base import *

# === DESENVOLVIMENTO ===

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# === APPS ADICIONAIS PARA DEV ===

INSTALLED_APPS += [
    'django_extensions',  # shell_plus, runserver_plus, etc
]

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

# Usar SQLite para desenvolvimento local se preferir
if env('USE_SQLITE', default=False):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

# Desabilitar cache em desenvolvimento
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
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