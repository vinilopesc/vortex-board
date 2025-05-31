# apps/core/urls.py

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # === AUTENTICAÇÃO ===
    # Sistema de login/logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Sistema de registro
    path('registro/', views.registro_view, name='registro'),

    # Sistema de recuperação de senha
    path('recuperar-senha/', views.recuperar_senha_view, name='recuperar_senha'),
    path('redefinir-senha/<str:token>/', views.redefinir_senha_view, name='redefinir_senha'),

    # === PAINEL PRINCIPAL ===
    path('painel/', views.painel_principal, name='painel'),
    path('', views.painel_principal, name='home'),  # Redirecionar root para painel

    # === PERFIL DO USUÁRIO ===
    path('perfil/', views.perfil_usuario, name='perfil'),

    # === PROJETOS ===
    # Modal para criar projeto (HTMX)
    path('projetos/criar/', views.criar_projeto_modal, name='criar_projeto_modal'),
    # Salvar projeto via POST
    path('projetos/salvar/', views.salvar_projeto, name='salvar_projeto'),

    # === MONITORAMENTO ===
    path('health/', views.health_check, name='health'),

    # === APIs AJAX ===
    path('api/painel/stats/', views.api_estatisticas_painel, name='api_stats_painel'),
    path('api/tarefas-urgentes/', views.api_tarefas_urgentes, name='api_tarefas_urgentes'),
]