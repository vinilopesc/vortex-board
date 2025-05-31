# apps/core/middleware.py

from django.http import Http404
from django.shortcuts import redirect
from django.contrib import messages


class MultiTenantSecurityMiddleware:
    """
    Middleware que garante isolamento de dados entre empresas

    Atua como uma segunda camada de proteção, verificando
    se usuários estão tentando acessar dados de outras empresas
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Processar request
        response = self.get_response(request)

        # Adicionar headers de segurança
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['X-Tenant'] = request.user.empresa
            response['X-User-Type'] = request.user.tipo

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Verificar acesso a recursos específicos antes da view ser executada
        """
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None  # Deixar sistema de auth padrão lidar com isso

        # Verificar acesso a projetos específicos
        if 'projeto_id' in view_kwargs:
            projeto_id = view_kwargs['projeto_id']
            try:
                from .models import Projeto
                projeto = Projeto.objects.get(id=projeto_id)

                if not request.user.pode_acessar_projeto(projeto):
                    messages.error(request, 'Você não tem acesso a este projeto.')
                    return redirect('core:painel')

            except Projeto.DoesNotExist:
                raise Http404("Projeto não encontrado")

        # Verificar acesso a boards específicos
        if 'board_id' in view_kwargs:
            board_id = view_kwargs['board_id']
            try:
                from apps.board.models import Board
                board = Board.objects.get(id=board_id)

                if not request.user.pode_acessar_projeto(board.projeto):
                    messages.error(request, 'Você não tem acesso a este board.')
                    return redirect('core:painel')

            except Board.DoesNotExist:
                raise Http404("Board não encontrado")

        return None  # Continuar processamento normal