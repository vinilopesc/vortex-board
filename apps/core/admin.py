# apps/core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    Usuario, Projeto, Board, Coluna, Bug, Feature,
    RegistroHora, Comentario
)


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Admin customizado para o modelo Usuario"""

    list_display = [
        'username', 'email', 'get_full_name', 'tipo_badge',
        'is_active', 'date_joined'
    ]
    list_filter = ['tipo', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']

    # Adicionar campos customizados ao formulário
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('tipo', 'telefone', 'foto')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('tipo', 'telefone')
        }),
    )

    def tipo_badge(self, obj):
        """Exibe o tipo de usuário com badge colorido"""
        cores = {
            'admin': '#EF4444',  # vermelho
            'gerente': '#F59E0B',  # amarelo
            'funcionario': '#3B82F6'  # azul
        }
        cor = cores.get(obj.tipo, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            cor, obj.get_tipo_display()
        )

    tipo_badge.short_description = 'Tipo'


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    """Admin para gerenciamento de projetos"""

    list_display = [
        'nome', 'cliente', 'criado_por', 'membros_count',
        'boards_count', 'ativo', 'criado_em'
    ]
    list_filter = ['ativo', 'criado_em', 'criado_por']
    search_fields = ['nome', 'cliente', 'descricao']
    filter_horizontal = ['membros']
    readonly_fields = ['criado_em', 'atualizado_em']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'cliente', 'descricao', 'ativo')
        }),
        ('Equipe', {
            'fields': ('criado_por', 'membros')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )

    def membros_count(self, obj):
        """Conta quantidade de membros"""
        return obj.membros.count()

    membros_count.short_description = 'Membros'

    def boards_count(self, obj):
        """Conta quantidade de boards"""
        return obj.boards.count()

    boards_count.short_description = 'Boards'


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    """Admin para boards Kanban"""

    list_display = [
        'titulo', 'projeto', 'colunas_count', 'items_count',
        'ativo', 'criado_em'
    ]
    list_filter = ['ativo', 'criado_em', 'projeto']
    search_fields = ['titulo', 'descricao', 'projeto__nome']
    readonly_fields = ['criado_em']

    def colunas_count(self, obj):
        """Conta colunas do board"""
        return obj.colunas.count()

    colunas_count.short_description = 'Colunas'

    def items_count(self, obj):
        """Conta total de items (bugs + features)"""
        bugs = Bug.objects.filter(coluna__board=obj).count()
        features = Feature.objects.filter(coluna__board=obj).count()
        return bugs + features

    items_count.short_description = 'Items'


class ItemInline(admin.TabularInline):
    """Inline base para items em colunas"""
    extra = 0
    fields = ['titulo', 'responsavel', 'prioridade', 'ordem']
    ordering = ['ordem']


class BugInline(ItemInline):
    """Inline para bugs"""
    model = Bug
    verbose_name = "Bug"
    verbose_name_plural = "Bugs"


class FeatureInline(ItemInline):
    """Inline para features"""
    model = Feature
    verbose_name = "Feature"
    verbose_name_plural = "Features"


class ComentarioInline(admin.TabularInline):
    """Inline para comentários - CORRIGIDO"""
    model = Comentario  # ADICIONADO: model é obrigatório
    extra = 0
    fields = ['usuario', 'texto', 'criado_em']
    readonly_fields = ['criado_em']

    def has_add_permission(self, request, obj=None):
        """Apenas leitura no admin"""
        return False


@admin.register(Coluna)
class ColunaAdmin(admin.ModelAdmin):
    """Admin para colunas do Kanban"""

    list_display = [
        'titulo', 'board', 'ordem', 'limite_wip',
        'items_count', 'cor_preview'
    ]
    list_filter = ['board__projeto', 'board']
    search_fields = ['titulo', 'board__titulo']
    ordering = ['board', 'ordem']

    inlines = [BugInline, FeatureInline]

    def items_count(self, obj):
        """Conta items na coluna"""
        bugs = obj.bug_items.filter(arquivado=False).count()
        features = obj.feature_items.filter(arquivado=False).count()
        total = bugs + features

        # Adicionar indicador de WIP
        if obj.limite_wip > 0 and total >= obj.limite_wip:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}/{}</span>',
                total, obj.limite_wip
            )
        elif obj.limite_wip > 0:
            return f"{total}/{obj.limite_wip}"
        return total

    items_count.short_description = 'Items/WIP'

    def cor_preview(self, obj):
        """Preview da cor da coluna"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; '
            'border: 1px solid #ccc; border-radius: 3px;"></div>',
            obj.cor
        )

    cor_preview.short_description = 'Cor'


@admin.register(Bug)
class BugAdmin(admin.ModelAdmin):
    """Admin para bugs"""

    list_display = [
        'id', 'titulo', 'severidade_badge', 'prioridade_badge',
        'responsavel', 'coluna', 'status_prazo', 'pontos'
    ]
    list_filter = [
        'severidade', 'prioridade', 'ambiente',
        'coluna__board', 'arquivado', 'criado_em'
    ]
    search_fields = ['titulo', 'descricao', 'passos_reproducao']
    date_hierarchy = 'criado_em'

    readonly_fields = [
        'criado_em', 'atualizado_em', 'criado_por',
        'calcular_pontos', 'esta_atrasado'
    ]

    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'titulo', 'descricao', 'coluna', 'responsavel',
                'prioridade', 'prazo', 'arquivado'
            )
        }),
        ('Detalhes do Bug', {
            'fields': (
                'severidade', 'ambiente', 'passos_reproducao'
            )
        }),
        ('Metadados', {
            'fields': (
                'ordem', 'criado_por', 'criado_em', 'atualizado_em',
                'calcular_pontos', 'esta_atrasado'
            ),
            'classes': ('collapse',)
        })
    )

    inlines = [ComentarioInline]

    def severidade_badge(self, obj):
        """Badge colorido para severidade"""
        cores = {
            'baixa': '#10B981',  # verde
            'media': '#F59E0B',  # amarelo
            'alta': '#F97316',  # laranja
            'critica': '#EF4444'  # vermelho
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            cores.get(obj.severidade, '#6B7280'),
            obj.get_severidade_display()
        )

    severidade_badge.short_description = 'Severidade'

    def prioridade_badge(self, obj):
        """Badge colorido para prioridade"""
        icons = {
            'baixa': '🟢',
            'media': '🟡',
            'alta': '🟠',
            'critica': '🔴'
        }
        return f"{icons.get(obj.prioridade, '')} {obj.get_prioridade_display()}"

    prioridade_badge.short_description = 'Prioridade'

    def status_prazo(self, obj):
        """Status do prazo"""
        if not obj.prazo:
            return '-'

        if obj.coluna.titulo == 'Concluído':
            return format_html('<span style="color: green;">✓ Concluído</span>')

        if obj.esta_atrasado():
            dias = (timezone.now().date() - obj.prazo).days
            return format_html(
                '<span style="color: red;">⚠️ Atrasado {} dias</span>',
                dias
            )

        dias = (obj.prazo - timezone.now().date()).days
        if dias == 0:
            return format_html('<span style="color: orange;">⏰ Vence hoje</span>')
        elif dias == 1:
            return format_html('<span style="color: orange;">⏰ Vence amanhã</span>')
        else:
            return f"Em {dias} dias"

    status_prazo.short_description = 'Prazo'

    def pontos(self, obj):
        """Exibe pontos calculados"""
        return f"{obj.calcular_pontos()} pts"

    pontos.short_description = 'Pontos'


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    """Admin para features"""

    list_display = [
        'id', 'titulo', 'categoria_icon', 'prioridade_badge',
        'responsavel', 'coluna', 'horas_estimadas', 'pontos'
    ]
    list_filter = [
        'categoria', 'prioridade', 'coluna__board',
        'arquivado', 'criado_em'
    ]
    search_fields = ['titulo', 'descricao']
    date_hierarchy = 'criado_em'

    readonly_fields = [
        'criado_em', 'atualizado_em', 'criado_por',
        'calcular_pontos', 'esta_atrasado'
    ]

    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'titulo', 'descricao', 'coluna', 'responsavel',
                'prioridade', 'prazo', 'arquivado'
            )
        }),
        ('Detalhes da Feature', {
            'fields': (
                'categoria', 'estimativa_horas', 'especificacao_url'
            )
        }),
        ('Metadados', {
            'fields': (
                'ordem', 'criado_por', 'criado_em', 'atualizado_em',
                'calcular_pontos', 'esta_atrasado'
            ),
            'classes': ('collapse',)
        })
    )

    inlines = [ComentarioInline]

    def categoria_icon(self, obj):
        """Ícone e nome da categoria"""
        return f"{obj.get_icon_categoria()} {obj.get_categoria_display()}"

    categoria_icon.short_description = 'Categoria'

    def prioridade_badge(self, obj):
        """Badge para prioridade"""
        icons = {
            'baixa': '🟢',
            'media': '🟡',
            'alta': '🟠',
            'critica': '🔴'
        }
        return f"{icons.get(obj.prioridade, '')} {obj.get_prioridade_display()}"

    prioridade_badge.short_description = 'Prioridade'

    def horas_estimadas(self, obj):
        """Formatação das horas"""
        return f"{obj.estimativa_horas}h"

    horas_estimadas.short_description = 'Estimativa'

    def pontos(self, obj):
        """Exibe pontos calculados"""
        return f"{obj.calcular_pontos()} pts"

    pontos.short_description = 'Pontos'


@admin.register(RegistroHora)
class RegistroHoraAdmin(admin.ModelAdmin):
    """Admin para registros de hora"""

    list_display = [
        'usuario', 'get_item', 'inicio', 'fim',
        'duracao_formatada', 'status'
    ]
    list_filter = ['usuario', 'inicio', 'fim']
    search_fields = ['descricao', 'usuario__username']
    date_hierarchy = 'inicio'
    readonly_fields = ['duracao']

    def get_item(self, obj):
        """Retorna o item associado"""
        item = obj.item
        if item:
            tipo = "🐛 Bug" if isinstance(item, Bug) else "✨ Feature"
            return f"{tipo}: {item.titulo}"
        return '-'

    get_item.short_description = 'Item'

    def duracao_formatada(self, obj):
        """Formata duração em horas"""
        if obj.duracao:
            horas = int(obj.duracao)
            minutos = int((obj.duracao - horas) * 60)
            return f"{horas}h {minutos}min"
        return '-'

    duracao_formatada.short_description = 'Duração'

    def status(self, obj):
        """Status do registro"""
        if obj.fim:
            return format_html(
                '<span style="color: green;">✓ Finalizado</span>'
            )
        return format_html(
            '<span style="color: orange;">⏱️ Em andamento</span>'
        )

    status.short_description = 'Status'


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """Admin para comentários"""

    list_display = [
        'usuario', 'get_item', 'texto_resumo',
        'criado_em', 'foi_editado'
    ]
    list_filter = ['criado_em', 'usuario']
    search_fields = ['texto', 'usuario__username']
    date_hierarchy = 'criado_em'
    readonly_fields = ['criado_em', 'editado_em']

    def get_item(self, obj):
        """Retorna item comentado"""
        if obj.bug:
            return f"🐛 {obj.bug.titulo}"
        elif obj.feature:
            return f"✨ {obj.feature.titulo}"
        return '-'

    get_item.short_description = 'Item'

    def texto_resumo(self, obj):
        """Resumo do texto do comentário"""
        if len(obj.texto) > 50:
            return f"{obj.texto[:50]}..."
        return obj.texto

    texto_resumo.short_description = 'Comentário'

    def foi_editado(self, obj):
        """Indica se foi editado"""
        if obj.editado_em:
            return format_html(
                '<span style="color: gray;">✏️ Editado</span>'
            )
        return '-'

    foi_editado.short_description = 'Editado'


# Configuração do site admin
admin.site.site_header = "Vortex Board - Administração"
admin.site.site_title = "Vortex Admin"
admin.site.index_title = "Painel Administrativo"