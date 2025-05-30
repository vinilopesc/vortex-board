# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Aplicações principais
    path('', include('apps.core.urls')),
    path('board/', include('apps.board.urls')),
    path('relatorios/', include('apps.relatorios.urls')),

    # Redirecionamentos úteis
    path('painel/', RedirectView.as_view(pattern_name='core:painel', permanent=False)),
    path('dashboard/', RedirectView.as_view(pattern_name='relatorios:dashboard', permanent=False)),
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug Toolbar se disponível
    try:
        import debug_toolbar

        urlpatterns = [
                          path('__debug__/', include(debug_toolbar.urls)),
                      ] + urlpatterns
    except ImportError:
        pass

# Customizar títulos do admin
admin.site.site_header = 'Vortex Board Admin'
admin.site.site_title = 'Vortex Board'
admin.site.index_title = 'Administração do Sistema'