# apps/core/urls.py

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Painel principal
    path('painel/', views.painel_view, name='painel'),

    # Perfil do usuário
    path('perfil/', views.perfil_view, name='perfil'),

    # Health check
    path('health/', views.health_check, name='health'),
]