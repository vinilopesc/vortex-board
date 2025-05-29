# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# URLs principais do projeto
urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),

    # Redirecionamento da raiz para painel
    path('', RedirectView.as_view(url='/painel/', permanent=False)),

    # Apps principais
    path('', include('apps.core.urls')),  # Login, painel, perfil
    path('board/', include('apps.board.urls')),  # Kanban boards
    path('relatorios/', include('apps.relatorios.urls')),  # Relatórios
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

    # Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]

# Configurações do Admin
admin.site.site_header = "Vortex Board - Administration"
admin.site.site_title = "Vortex Admin"
admin.site.index_title = "Painel Administrativo"

# Handler de erros customizados (opcional)
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'