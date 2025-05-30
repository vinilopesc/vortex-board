# apps/core/urls.py

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Painel principal
    path('painel/', views.painel_principal, name='painel'),
    path('', views.painel_principal, name='home'),  # Redirecionar root para painel

    # Perfil do usuário
    path('perfil/', views.perfil_usuario, name='perfil'),

    # Projetos
    path('projetos/criar/', views.criar_projeto, name='criar_projeto'),

    # Health check e monitoramento
    path('health/', views.health_check, name='health'),

    # APIs AJAX
    path('api/painel/stats/', views.api_estatisticas_painel, name='api_stats_painel'),
    path('api/tarefas-urgentes/', views.api_tarefas_urgentes, name='api_tarefas_urgentes'),
]