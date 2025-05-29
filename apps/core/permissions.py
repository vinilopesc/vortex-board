# apps/core/permissions.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


class VortexPermissions:
    """
    Sistema de permissões customizado do Vortex Board
    Baseado nos tipos de usuário: admin, gerente, funcionário
    """

    @staticmethod
    def is_admin(user):
        """Verifica se é administrador"""
        return user.is_authenticated and user.tipo == 'admin'

    @staticmethod
    def is_gerente(user):
        """Verifica se é gerente"""
        return user.is_authenticated and user.tipo == 'gerente'

    @staticmethod
    def is_funcionario(user):
        """Verifica se é funcionário"""
        return user.is_authenticated and user.tipo == 'funcionario'

    @staticmethod
    def is_gerente_ou_admin(user):
        """Verifica se é gerente ou admin"""
        return user.is_authenticated and user.tipo in ['admin', 'gerente']

    @staticmethod
    def pode_criar_projeto(user):
        """Verifica se pode criar projetos"""
        return user.is_authenticated and user.pode_criar_projeto()

    @staticmethod
    def pode_deletar_tarefa(user):
        """Verifica se pode deletar tarefas"""
        return user.is_authenticated and user.pode_deletar_tarefa()

    @staticmethod
    def pode_editar_projeto(user, projeto):
        """Verifica se pode editar um projeto específico"""
        if not user.is_authenticated:
            return False

        # Admin pode editar qualquer projeto
        if user.tipo == 'admin':
            return True

        # Criador do projeto pode editar
        if projeto.criado_por == user:
            return True

        # Gerente membro do projeto pode editar
        if user.tipo == 'gerente' and user in projeto.membros.all():
            return True

        return False

    @staticmethod
    def pode_editar_item(user, item):
        """Verifica se pode editar um item (bug/feature)"""
        if not user.is_authenticated:
            return False

        # Admin pode editar qualquer item
        if user.tipo == 'admin':
            return True

        # Criador do item pode editar
        if item.criado_por == user:
            return True

        # Responsável pode editar
        if item.responsavel == user:
            return True

        # Gerente do projeto pode editar
        if user.tipo == 'gerente':
            projeto = item.coluna.board.projeto
            if user in projeto.membros.all():
                return True

        return False

    @staticmethod
    def pode_mover_item(user, item):
        """Verifica se pode mover item entre colunas"""
        if not user.is_authenticated:
            return False

        # Admin e gerente podem mover qualquer item
        if user.tipo in ['admin', 'gerente']:
            projeto = item.coluna.board.projeto
            if user in projeto.membros.all():
                return True

        # Funcionário só pode mover seus próprios items
        if user.tipo == 'funcionario':
            if item.responsavel == user:
                return True

        return False

    @staticmethod
    def pode_comentar_item(user, item):
        """Verifica se pode comentar em um item"""
        if not user.is_authenticated:
            return False

        # Qualquer membro do projeto pode comentar
        projeto = item.coluna.board.projeto
        return user in projeto.membros.all()

    @staticmethod
    def pode_registrar_hora(user, item):
        """Verifica se pode registrar horas em um item"""
        if not user.is_authenticated:
            return False

        # Apenas responsável pode registrar horas
        return item.responsavel == user

    @staticmethod
    def tem_acesso_projeto(user, projeto):
        """Verifica se tem acesso ao projeto"""
        if not user.is_authenticated:
            return False

        # Admin tem acesso a todos os projetos
        if user.tipo == 'admin':
            return True

        # Outros usuários precisam ser membros
        return user in projeto.membros.all()

    @staticmethod
    def tem_acesso_board(user, board):
        """Verifica se tem acesso ao board"""
        return VortexPermissions.tem_acesso_projeto(user, board.projeto)


# Decoradores para views

def requer_admin(view_func):
    """Decorador que requer usuário admin"""

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not VortexPermissions.is_admin(request.user):
            messages.error(request, 'Acesso negado. Apenas administradores.')
            return redirect('painel')
        return view_func(request, *args, **kwargs)

    return wrapped_view


def requer_gerente_ou_admin(view_func):
    """Decorador que requer gerente ou admin"""

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not VortexPermissions.is_gerente_ou_admin(request.user):
            messages.error(request, 'Acesso negado. Apenas gerentes e administradores.')
            return redirect('painel')
        return view_func(request, *args, **kwargs)

    return wrapped_view


def requer_acesso_projeto(view_func):
    """
    Decorador que verifica acesso ao projeto
    Espera que a view receba projeto_id como parâmetro
    """

    @wraps(view_func)
    def wrapped_view(request, projeto_id, *args, **kwargs):
        from .models import Projeto

        try:
            projeto = Projeto.objects.get(id=projeto_id)
        except Projeto.DoesNotExist:
            messages.error(request, 'Projeto não encontrado.')
            return redirect('painel')

        if not VortexPermissions.tem_acesso_projeto(request.user, projeto):
            messages.error(request, 'Você não tem acesso a este projeto.')
            return redirect('painel')

        # Adiciona o projeto ao request para uso na view
        request.projeto = projeto
        return view_func(request, projeto_id, *args, **kwargs)

    return wrapped_view


def requer_acesso_board(view_func):
    """
    Decorador que verifica acesso ao board
    Espera que a view receba board_id como parâmetro
    """

    @wraps(view_func)
    def wrapped_view(request, board_id, *args, **kwargs):
        from .models import Board

        try:
            board = Board.objects.select_related('projeto').get(id=board_id)
        except Board.DoesNotExist:
            messages.error(request, 'Board não encontrado.')
            return redirect('painel')

        if not VortexPermissions.tem_acesso_board(request.user, board):
            messages.error(request, 'Você não tem acesso a este board.')
            return redirect('painel')

        # Adiciona o board ao request para uso na view
        request.board = board
        return view_func(request, board_id, *args, **kwargs)

    return wrapped_view


def ajax_requer_permissao(permission_check):
    """
    Decorador genérico para views AJAX/HTMX
    Retorna 403 ao invés de redirecionar
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not permission_check(request.user):
                raise PermissionDenied("Você não tem permissão para esta ação.")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


# Mixins para Class-Based Views

class AdminRequiredMixin:
    """Mixin que requer usuário admin"""

    def dispatch(self, request, *args, **kwargs):
        if not VortexPermissions.is_admin(request.user):
            messages.error(request, 'Acesso negado. Apenas administradores.')
            return redirect('painel')
        return super().dispatch(request, *args, **kwargs)


class GerenteOuAdminRequiredMixin:
    """Mixin que requer gerente ou admin"""

    def dispatch(self, request, *args, **kwargs):
        if not VortexPermissions.is_gerente_ou_admin(request.user):
            messages.error(request, 'Acesso negado. Apenas gerentes e administradores.')
            return redirect('painel')
        return super().dispatch(request, *args, **kwargs)


class ProjetoAccessMixin:
    """Mixin que verifica acesso ao projeto"""

    def dispatch(self, request, *args, **kwargs):
        from .models import Projeto

        projeto_id = kwargs.get('projeto_id')
        if not projeto_id:
            messages.error(request, 'Projeto não especificado.')
            return redirect('painel')

        try:
            self.projeto = Projeto.objects.get(id=projeto_id)
        except Projeto.DoesNotExist:
            messages.error(request, 'Projeto não encontrado.')
            return redirect('painel')

        if not VortexPermissions.tem_acesso_projeto(request.user, self.projeto):
            messages.error(request, 'Você não tem acesso a este projeto.')
            return redirect('painel')

        return super().dispatch(request, *args, **kwargs)


class BoardAccessMixin:
    """Mixin que verifica acesso ao board"""

    def dispatch(self, request, *args, **kwargs):
        from .models import Board

        board_id = kwargs.get('board_id')
        if not board_id:
            messages.error(request, 'Board não especificado.')
            return redirect('painel')

        try:
            self.board = Board.objects.select_related('projeto').get(id=board_id)
        except Board.DoesNotExist:
            messages.error(request, 'Board não encontrado.')
            return redirect('painel')

        if not VortexPermissions.tem_acesso_board(request.user, self.board):
            messages.error(request, 'Você não tem acesso a este board.')
            return redirect('painel')

        return super().dispatch(request, *args, **kwargs)