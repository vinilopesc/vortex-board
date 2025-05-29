# apps/relatorios/urls.py

from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_relatorios, name='dashboard'),

    # Relatórios de projeto
    path('projeto/<int:projeto_id>/pdf/', views.relatorio_projeto_pdf, name='projeto_pdf'),
    path('projeto/<int:projeto_id>/csv/', views.exportar_projeto_csv, name='projeto_csv'),
    path('projeto/<int:projeto_id>/excel/', views.exportar_projeto_excel, name='projeto_excel'),

    # Relatórios de horas
    path('horas/', views.relatorio_horas_usuario, name='horas_usuario'),

    # APIs para dashboards
    path('api/metricas/', views.api_metricas_dashboard, name='api_metricas'),
]