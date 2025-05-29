# apps/board/routing.py

from django.urls import re_path
from . import consumers

# Rotas WebSocket para a aplicação board
websocket_urlpatterns = [
    # WebSocket para board específico - atualizações em tempo real
    re_path(r'ws/board/(?P<board_id>\d+)/$', consumers.BoardConsumer.as_asgi()),

    # WebSocket para notificações gerais do usuário
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]