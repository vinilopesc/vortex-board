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
            if os.system('python manage.py migrate') != 0:
                print("❌ Erro nas migrações")
                return

            # Coletar arquivos estáticos
            print("📁 Coletando arquivos estáticos...")
            os.system('python manage.py collectstatic --noinput')

            # Criar superusuário se não existir
            print("👤 Verificando superusuário...")
            exit_code = os.system(
                'python manage.py shell -c "from apps.core.models import Usuario; Usuario.objects.filter(is_superuser=True).exists() or Usuario.objects.create_superuser(\'admin\', \'admin@vortex.com.br\', \'admin123\', tipo=\'admin\')"')

            if exit_code == 0:
                # Executar seed apenas se não houver erro
                print("🌱 Populando banco com dados demo...")
                os.system('python manage.py seed')

                print("✅ Setup concluído!")
                print("🔑 Acesse com: admin/admin123")
            else:
                print("⚠️  Setup parcial concluído (sem dados demo)")
            return

        # Comando de configuração do banco
        elif command == 'setup-db':
            print("🐘 Configurando PostgreSQL...")

            # Comandos SQL para executar
            commands = [
                "CREATE USER vortex_user WITH PASSWORD 'vortex123';",
                "CREATE DATABASE vortex_board OWNER vortex_user;",
                "GRANT ALL PRIVILEGES ON DATABASE vortex_board TO vortex_user;",
                "GRANT CREATE ON SCHEMA public TO vortex_user;",
                "ALTER USER vortex_user CREATEDB;"
            ]

            for cmd in commands:
                print(f"Executando: {cmd}")
                exit_code = os.system(f'psql -U postgres -h localhost -c "{cmd}"')
                if exit_code != 0:
                    print(f"⚠️  Comando pode ter falhado (normal se já existir)")

            # Testar conexão
            print("🧪 Testando conexão...")
            test_result = os.system('psql -U vortex_user -h localhost -d vortex_board -c "SELECT version();"')

            if test_result == 0:
                print("✅ PostgreSQL configurado com sucesso!")
                print("📊 Execute agora: python manage.py setup")
            else:
                print("❌ Erro na configuração. Verifique:")
                print("   1. PostgreSQL está instalado?")
                print("   2. Serviço postgresql está rodando?")
                print("   3. psql está no PATH?")
                print("   4. Senha do postgres está correta?")
            return
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