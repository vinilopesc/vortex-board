# apps/board/apps.py

from django.apps import AppConfig


class BoardConfig(AppConfig):
    """Configuração da app Board"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.board'
    verbose_name = 'Board - Kanban'

    def ready(self):
        """
        Inicialização da app
        Registra sinais, configurações WebSocket
        """
        # Importar sinais se houver
        try:
            from . import signals
        except ImportError:
            pass

        # Log de inicialização
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🔌 Board App inicializada - WebSockets habilitados")