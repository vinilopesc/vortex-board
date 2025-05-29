# apps/board/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from apps.core.models import Board
from apps.core.permissions import VortexPermissions

logger = logging.getLogger(__name__)
Usuario = get_user_model()


class BoardConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para atualizações em tempo real do board Kanban

    Funcionalidades:
    - Notificações de movimentação de cards
    - Updates de comentários
    - Indicação de usuários online
    - Sincronização automática
    """

    async def connect(self):
        """
        Conecta usuário ao grupo do board
        Verifica permissões antes de aceitar conexão
        """
        self.board_id = self.scope['url_route']['kwargs']['board_id']
        self.board_group_name = f'board_{self.board_id}'
        self.user = self.scope['user']

        # Verificar se usuário está autenticado
        if not self.user.is_authenticated:
            logger.warning(f"❌ Conexão WebSocket rejeitada - usuário não autenticado")
            await self.close()
            return

        # Verificar permissão de acesso ao board
        has_access = await self.check_board_access()
        if not has_access:
            logger.warning(f"❌ Conexão WebSocket rejeitada - {self.user.username} sem acesso ao board {self.board_id}")
            await self.close()
            return

        # Juntar ao grupo do board
        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name
        )

        # Aceitar conexão
        await self.accept()

        # Notificar outros usuários que alguém entrou
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'user_joined',
                'message': {
                    'usuario': self.user.get_full_name() or self.user.username,
                    'user_id': self.user.id,
                    'timestamp': self.get_timestamp()
                }
            }
        )

        logger.info(f"✅ WebSocket conectado - {self.user.username} no board {self.board_id}")

    async def disconnect(self, close_code):
        """
        Desconecta usuário do grupo
        """
        if hasattr(self, 'board_group_name'):
            # Notificar outros usuários que alguém saiu
            await self.channel_layer.group_send(
                self.board_group_name,
                {
                    'type': 'user_left',
                    'message': {
                        'usuario': self.user.get_full_name() or self.user.username,
                        'user_id': self.user.id,
                        'timestamp': self.get_timestamp()
                    }
                }
            )

            # Sair do grupo
            await self.channel_layer.group_discard(
                self.board_group_name,
                self.channel_name
            )

        logger.info(f"🔌 WebSocket desconectado - {self.user.username} do board {self.board_id}")

    async def receive(self, text_data):
        """
        Recebe mensagens do cliente WebSocket
        Processa diferentes tipos de eventos
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            # Heartbeat/Ping
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': self.get_timestamp()
                }))
                return

            # Notificação de usuário digitando comentário
            elif message_type == 'typing_comment':
                await self.channel_layer.group_send(
                    self.board_group_name,
                    {
                        'type': 'user_typing',
                        'message': {
                            'usuario': self.user.get_full_name() or self.user.username,
                            'user_id': self.user.id,
                            'item_id': data.get('item_id'),
                            'item_type': data.get('item_type'),
                            'is_typing': data.get('is_typing', True),
                            'timestamp': self.get_timestamp()
                        }
                    }
                )

            # Sincronização de estado do board
            elif message_type == 'sync_board':
                board_data = await self.get_board_state()
                await self.send(text_data=json.dumps({
                    'type': 'board_sync',
                    'board_data': board_data,
                    'timestamp': self.get_timestamp()
                }))

        except json.JSONDecodeError:
            logger.error(f"❌ JSON inválido recebido via WebSocket de {self.user.username}")
        except Exception as e:
            logger.error(f"❌ Erro no WebSocket receive: {str(e)}")

    # === Handlers para diferentes tipos de eventos ===

    async def item_moved(self, event):
        """
        Notifica sobre movimentação de item
        """
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'item_moved',
            'message': message
        }))

    async def item_created(self, event):
        """
        Notifica sobre criação de novo item
        """
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'item_created',
            'message': message
        }))

    async def comment_added(self, event):
        """
        Notifica sobre novo comentário
        """
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'comment_added',
            'message': message
        }))

    async def user_joined(self, event):
        """
        Notifica quando usuário entra no board
        """
        message = event['message']
        # Não enviar para o próprio usuário
        if message['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'message': message
            }))

    async def user_left(self, event):
        """
        Notifica quando usuário sai do board
        """
        message = event['message']
        # Não enviar para o próprio usuário
        if message['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'message': message
            }))

    async def user_typing(self, event):
        """
        Notifica quando usuário está digitando
        """
        message = event['message']
        # Não enviar para o próprio usuário
        if message['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'message': message
            }))

    async def board_refresh(self, event):
        """
        Força refresh do board (para grandes mudanças)
        """
        await self.send(text_data=json.dumps({
            'type': 'board_refresh',
            'message': event['message']
        }))

    # === Métodos auxiliares ===

    @database_sync_to_async
    def check_board_access(self):
        """
        Verifica se usuário tem acesso ao board
        """
        try:
            board = Board.objects.select_related('projeto').get(id=self.board_id)
            return VortexPermissions.tem_acesso_board(self.user, board)
        except Board.DoesNotExist:
            return False

    @database_sync_to_async
    def get_board_state(self):
        """
        Retorna estado atual do board para sincronização
        """
        try:
            from apps.core.models import Bug, Feature

            board = Board.objects.get(id=self.board_id)

            # Contar items por coluna
            colunas_data = []
            for coluna in board.colunas.order_by('ordem'):
                bugs_count = Bug.objects.filter(coluna=coluna, arquivado=False).count()
                features_count = Feature.objects.filter(coluna=coluna, arquivado=False).count()

                colunas_data.append({
                    'id': coluna.id,
                    'titulo': coluna.titulo,
                    'bugs_count': bugs_count,
                    'features_count': features_count,
                    'total_items': bugs_count + features_count,
                    'limite_wip': coluna.limite_wip,
                    'cor': coluna.cor
                })

            return {
                'board_id': board.id,
                'titulo': board.titulo,
                'colunas': colunas_data
            }

        except Exception as e:
            logger.error(f"❌ Erro ao obter estado do board: {str(e)}")
            return {}

    def get_timestamp(self):
        """
        Retorna timestamp atual em formato ISO
        """
        from django.utils import timezone
        return timezone.now().isoformat()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer para notificações gerais do usuário
    (separado do board para permitir notificações globais)
    """

    async def connect(self):
        """
        Conecta usuário ao seu grupo pessoal de notificações
        """
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f'user_{self.user.id}'

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"🔔 Notificações conectadas para {self.user.username}")

    async def disconnect(self, close_code):
        """
        Desconecta das notificações
        """
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

        logger.info(f"🔕 Notificações desconectadas para {self.user.username}")

    async def receive(self, text_data):
        """
        Processa comandos de notificação
        """
        try:
            data = json.loads(text_data)

            # Marcar notificação como lida
            if data.get('type') == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)

        except Exception as e:
            logger.error(f"❌ Erro no NotificationConsumer: {str(e)}")

    async def notification_message(self, event):
        """
        Envia notificação para o usuário
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message']
        }))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """
        Marca notificação como lida
        """
        # TODO: Implementar modelo de Notificação
        pass