# config/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Definir configurações antes de importar aplicação Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Inicializar Django
django_asgi_app = get_asgi_application()

# Importar roteamento WebSocket após inicializar Django
from apps.board.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP requests
    "http": django_asgi_app,

    # WebSocket chat handler
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})