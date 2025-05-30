# config/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# Configurar settings padrão
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Obter aplicação WSGI
application = get_wsgi_application()