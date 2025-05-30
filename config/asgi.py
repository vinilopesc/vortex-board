# config/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Configurar Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Importar URLs de WebSocket depois de configurar Django
django_asgi_app = get_asgi_application()

try:
    from apps.board.routing import websocket_urlpatterns
except ImportError:
    # Fallback caso não exista routing
    websocket_urlpatterns = []

# Configuração ASGI
application = ProtocolTypeRouter({
    # HTTP tradicional
    "http": django_asgi_app,

    # WebSocket com autenticação
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})