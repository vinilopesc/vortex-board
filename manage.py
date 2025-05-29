#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

Vortex Board - Sistema Kanban
Startup Vórtex © 2024
"""

import os
import sys


def main():
    """Run administrative tasks."""

    # Configuração padrão para desenvolvimento
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Comandos customizados do Vortex Board
    if len(sys.argv) > 1:
        command = sys.argv[1]

        # Comando de setup inicial
        if command == 'setup':
            print("🚀 Configurando Vortex Board...")

            # Executar migrações
            print("📊 Aplicando migrações...")
            os.system('python manage.py migrate')

            # Coletar arquivos estáticos
            print("📁 Coletando arquivos estáticos...")
            os.system('python manage.py collectstatic --noinput')

            # Criar superusuário se não existir
            print("👤 Verificando superusuário...")
            os.system(
                'python manage.py shell -c "from apps.core.models import Usuario; Usuario.objects.filter(is_superuser=True).exists() or Usuario.objects.create_superuser(\'admin\', \'admin@vortex.com.br\', \'admin123\')"')

            # Executar seed
            print("🌱 Populando banco com dados demo...")
            os.system('python manage.py seed')

            print("✅ Setup concluído!")
            print("🔑 Acesse com: admin/admin123")
            return

        # Comando de backup
        elif command == 'backup':
            print("💾 Criando backup do banco...")
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_vortex_{timestamp}.json"
            os.system(f'python manage.py dumpdata --indent 2 > {backup_file}')
            print(f"✅ Backup criado: {backup_file}")
            return

        # Comando de reset
        elif command == 'reset':
            confirm = input("⚠️  Isso irá apagar TODOS os dados. Continuar? (y/N): ")
            if confirm.lower() == 'y':
                print("🗑️  Resetando banco de dados...")
                os.system('python manage.py flush --noinput')
                os.system('python manage.py migrate')
                os.system('python manage.py seed')
                print("✅ Reset concluído!")
            return

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()