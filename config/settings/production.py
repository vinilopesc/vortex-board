# config/settings/production.py

import os
import dj_database_url
from .base import *

# === PRODUÇÃO ===

DEBUG = False

# Hosts permitidos (obrigatório definir)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default=[
    'vortex-board.com',
    'www.vortex-board.com',
    '*.amazonaws.com',
    '*.lightsail.aws',
])

# === SEGURANÇA ===

# SSL/HTTPS obrigatório
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Outros cabeçalhos de segurança
X_FRAME_OPTIONS = 'DENY'

# === BANCO DE DADOS ===

# Usar DATABASE_URL em produção (Heroku, Railway, etc)
if env('DATABASE_URL', default=None):
    DATABASES['default'] = dj_database_url.parse(
        env('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
else:
    # Configuração manual para outros provedores
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT', default='5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
            'CONN_MAX_AGE': 600,
        }
    }

# === EMAIL ===

# Configurar SMTP real em produção
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = env('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@vortex.com.br')

# === LOGGING ===

# Logging mais robusto para produção
LOGGING['handlers']['file']['filename'] = '/var/log/vortex-board/vortex.log'

# Logging para Sentry (se configurado)
if env('SENTRY_DSN', default=None):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )

    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment=env('ENVIRONMENT', default='production')
    )

# === CACHE ===

# Redis obrigatório em produção
if not env('REDIS_URL', default=None):
    raise ValueError("REDIS_URL é obrigatório em produção")

# Cache para sessões
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# === ARQUIVOS ESTÁTICOS ===

# AWS S3 para arquivos estáticos (opcional)
if env('USE_S3', cast=bool, default=False):
    # pip install django-storages boto3
    INSTALLED_APPS += ['storages']

    # Configurações S3
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

    # Arquivos estáticos
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

    # Arquivos de mídia
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# === CONFIGURAÇÕES DE PERFORMANCE ===

# Compressão de responses
MIDDLEWARE = ['django.middleware.gzip.GZipMiddleware'] + MIDDLEWARE

# Cache de templates
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# === MONITORAMENTO ===

# Health checks
INSTALLED_APPS += ['health_check']

HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # 90% max usage
    'MEMORY_MIN': 100,  # 100MB min memory
}

# === CONFIGURAÇÕES ESPECÍFICAS AWS LIGHTSAIL ===

if env('AWS_LIGHTSAIL', cast=bool, default=False):
    # Configurações específicas para Lightsail
    ALLOWED_HOSTS += [
        '*.amazonaws.com',
        env('LIGHTSAIL_HOST', default='')
    ]

    # Logs para CloudWatch (se configurado)
    if env('AWS_CLOUDWATCH_LOG_GROUP', default=None):
        LOGGING['handlers']['cloudwatch'] = {
            'level': 'INFO',
            'class': 'watchtower.CloudWatchLogHandler',
            'log_group': env('AWS_CLOUDWATCH_LOG_GROUP'),
            'stream_name': 'vortex-board-{strftime:%Y-%m-%d}',
        }
        LOGGING['root']['handlers'].append('cloudwatch')

# === VALIDAÇÕES ===

# Verificar variáveis obrigatórias
required_settings = ['SECRET_KEY']
if env('DATABASE_URL', default=None) is None:
    required_settings.extend(['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST'])

for setting in required_settings:
    if not env(setting, default=None):
        raise ValueError(f"Variável de ambiente {setting} é obrigatória em produção")

print("🚀 Configurações de PRODUÇÃO carregadas")
print(f"🔒 DEBUG: {DEBUG}")
print(f"🌐 ALLOWED_HOSTS: {ALLOWED_HOSTS[:3]}...")  # Mostrar apenas os 3 primeiros