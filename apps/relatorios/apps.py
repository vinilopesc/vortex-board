# apps/relatorios/apps.py

from django.apps import AppConfig


class RelatoriosConfig(AppConfig):
    """Configuração da app Relatórios"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.relatorios'
    verbose_name = 'Relatórios - PDF & Exports'

    def ready(self):
        """
        Inicialização da app
        Registra tarefas de relatórios, configurações
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Relatorios App inicializada - ReportLab habilitado")