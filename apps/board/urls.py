# apps/board/urls.py

from django.urls import path
from . import views

app_name = 'board'

urlpatterns = [
    # Kanban principal
    path('<int:board_id>/', views.board_kanban_view, name='kanban'),

    # AJAX/HTMX - Movimentação de items
    path('mover-item/', views.mover_item_ajax, name='mover_item'),

    # Criação de items
    path('<int:board_id>/criar-item/', views.criar_item_modal, name='criar_item'),

    # Detalhes de items
    path('item/<str:item_type>/<int:item_id>/', views.detalhes_item_modal, name='detalhes_item'),

    # Comentários
    path('item/<str:item_type>/<int:item_id>/comentar/', views.adicionar_comentario, name='adicionar_comentario'),

    # Registros de hora
    path('item/<str:item_type>/<int:item_id>/iniciar-hora/', views.iniciar_registro_hora, name='iniciar_registro_hora'),
    path('registro-hora/<int:registro_id>/finalizar/', views.finalizar_registro_hora, name='finalizar_registro_hora'),

    # Busca e filtros
    path('<int:board_id>/buscar/', views.buscar_items, name='buscar_items'),

    # Métricas e analytics
    path('<int:board_id>/metricas/', views.board_metricas, name='metricas'),
]