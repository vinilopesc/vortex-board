# apps/core/management/commands/migrar_empresas.py

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Usuario


class Command(BaseCommand):
    help = 'Migra usuários existentes para ter campo empresa preenchido'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-padrao',
            type=str,
            default='Empresa Padrão',
            help='Nome da empresa padrão para usuários existentes'
        )

    def handle(self, *args, **options):
        empresa_padrao = options['empresa_padrao']

        with transaction.atomic():
            # Buscar usuários sem empresa definida
            usuarios_sem_empresa = Usuario.objects.filter(
                models.Q(empresa__isnull=True) | models.Q(empresa='')
            )

            count = usuarios_sem_empresa.count()

            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS('✅ Todos os usuários já possuem empresa definida')
                )
                return

            # Atualizar usuários
            usuarios_sem_empresa.update(empresa=empresa_padrao)

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {count} usuários migrados para empresa "{empresa_padrao}"'
                )
            )

            # Mostrar usuários migrados
            for usuario in usuarios_sem_empresa:
                self.stdout.write(f'  - {usuario.username} → {empresa_padrao}')