# apps/core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuração da app Core"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core - Sistema Base'

    def ready(self):
        """
        Método chamado quando a aplicação está pronta
        Pode ser usado para conectar sinais, etc
        """
        # Importar sinais se houver
        try:
            from . import signals
        except ImportError:
            pass