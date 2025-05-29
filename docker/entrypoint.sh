#!/bin/bash

# docker/entrypoint.sh
# Entrypoint para container Docker do Vortex Board

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Vortex Board...${NC}"

# Função para aguardar serviços
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3

    echo -e "${YELLOW}⏳ Waiting for $service at $host:$port...${NC}"

    while ! nc -z $host $port; do
        sleep 1
    done

    echo -e "${GREEN}✅ $service is ready!${NC}"
}

# Aguardar PostgreSQL
if [ -n "$DATABASE_URL" ] || [ -n "$DB_HOST" ]; then
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}
    wait_for_service $DB_HOST $DB_PORT "PostgreSQL"
fi

# Aguardar Redis
if [ -n "$REDIS_URL" ]; then
    # Extrair host e porta do REDIS_URL
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's/redis:\/\/\([^:]*\).*/\1/p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's/redis:\/\/[^:]*:\([0-9]*\).*/\1/p')
    REDIS_HOST=${REDIS_HOST:-localhost}
    REDIS_PORT=${REDIS_PORT:-6379}
    wait_for_service $REDIS_HOST $REDIS_PORT "Redis"
fi

# Aplicar migrações
echo -e "${BLUE}📊 Running database migrations...${NC}"
python manage.py migrate --noinput

# Coletar arquivos estáticos
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ]; then
    echo -e "${BLUE}📁 Collecting static files...${NC}"
    python manage.py collectstatic --noinput --clear
fi

# Criar superusuário se não existir (apenas desenvolvimento)
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.development" ]; then
    echo -e "${BLUE}👤 Creating superuser if needed...${NC}"
    python manage.py shell -c "
from apps.core.models import Usuario
if not Usuario.objects.filter(is_superuser=True).exists():
    Usuario.objects.create_superuser('admin', 'admin@vortex.com.br', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

    # Popular com dados demo
    echo -e "${BLUE}🌱 Seeding database...${NC}"
    python manage.py seed --clear
fi

# Executar comando passado como argumento
if [ "$1" = "web" ]; then
    echo -e "${GREEN}🌐 Starting web server...${NC}"

    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ]; then
        # Produção: usar Gunicorn com worker ASGI
        exec gunicorn config.asgi:application \
            --bind 0.0.0.0:8000 \
            --worker-class uvicorn.workers.UvicornWorker \
            --workers 4 \
            --timeout 120 \
            --keep-alive 5 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --log-level info \
            --access-logfile - \
            --error-logfile -
    else
        # Desenvolvimento: usar servidor Django
        exec python manage.py runserver 0.0.0.0:8000
    fi

elif [ "$1" = "worker" ]; then
    echo -e "${GREEN}⚙️ Starting Celery worker...${NC}"
    exec celery -A config worker --loglevel=info

elif [ "$1" = "beat" ]; then
    echo -e "${GREEN}⏰ Starting Celery beat...${NC}"
    exec celery -A config beat --loglevel=info

elif [ "$1" = "migrate" ]; then
    echo -e "${GREEN}📊 Running migrations only...${NC}"
    exec python manage.py migrate

elif [ "$1" = "shell" ]; then
    echo -e "${GREEN}🐚 Starting Django shell...${NC}"
    exec python manage.py shell_plus

elif [ "$1" = "test" ]; then
    echo -e "${GREEN}🧪 Running tests...${NC}"
    exec python manage.py test

elif [ "$1" = "seed" ]; then
    echo -e "${GREEN}🌱 Seeding database...${NC}"
    exec python manage.py seed

else
    # Executar comando customizado
    echo -e "${GREEN}🔧 Running custom command: $@${NC}"
    exec "$@"
fi