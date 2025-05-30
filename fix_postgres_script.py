# fix_postgres.py
# Script para recriar banco PostgreSQL com encoding correto

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def recriar_banco():
    """Recria banco PostgreSQL com UTF-8"""
    
    print("🔧 Recriando banco PostgreSQL...")
    
    # Configurações
    DB_CONFIG = {
        'host': 'localhost',
        'port': '5432',
        'user': 'postgres',  # Usuário administrador
        'database': 'postgres'  # Banco padrão
    }
    
    # Solicitar senha do postgres
    senha_postgres = input("Digite a senha do usuário 'postgres': ")
    DB_CONFIG['password'] = senha_postgres
    
    try:
        # Conectar como admin
        print("📡 Conectando como administrador...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Desconectar sessões ativas
        print("🔌 Desconectando sessões ativas...")
        cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'vortex_board'
              AND pid <> pg_backend_pid()
        """)
        
        # Dropar banco se existir
        print("🗑️ Removendo banco antigo...")
        cursor.execute("DROP DATABASE IF EXISTS vortex_board")
        
        # Dropar usuário se existir
        cursor.execute("DROP USER IF EXISTS vortex_user")
        
        # Criar usuário
        print("👤 Criando usuário vortex_user...")
        cursor.execute("""
            CREATE USER vortex_user WITH PASSWORD 'vortex123'
        """)
        
        # Criar banco com UTF-8
        print("🏗️ Criando banco com UTF-8...")
        cursor.execute("""
            CREATE DATABASE vortex_board
            OWNER vortex_user
            ENCODING 'UTF8'
            LC_COLLATE 'C'
            LC_CTYPE 'C'
            TEMPLATE template0
        """)
        
        # Dar permissões
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE vortex_board TO vortex_user")
        cursor.execute("ALTER USER vortex_user CREATEDB")
        
        cursor.close()
        conn.close()
        
        print("✅ Banco recriado com sucesso!")
        print("🔄 Execute agora:")
        print("   python manage.py migrate")
        print("   python manage.py seed")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    recriar_banco()