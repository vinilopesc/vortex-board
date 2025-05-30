# apps/core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from abc import ABC, abstractmethod
import hashlib


class Usuario(AbstractUser):
    """
    Modelo customizado de usuário
    Demonstra conceitos de POO sem quebrar convenções do Django
    """

    TIPO_USUARIO_CHOICES = [
        ('admin', 'Administrador'),
        ('gerente', 'Gerente'),
        ('funcionario', 'Funcionário'),
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default='funcionario'
    )
    foto = models.ImageField(upload_to='perfis/', null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    # REMOVIDO: Campo __senha_hash que causava erro no Django
    # O Django já gerencia hash de senhas de forma segura via password field

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_tipo_display()})"

    def pode_criar_projeto(self):
        """Verifica permissão baseada no tipo de usuário"""
        return self.tipo in ['admin', 'gerente']

    def pode_deletar_tarefa(self):
        """Apenas admin pode deletar tarefas"""
        return self.tipo == 'admin'

    def gerar_cor_avatar(self):
        """Gera cor consistente para avatar baseada no username"""
        hash_obj = hashlib.md5(self.username.encode())
        return f"#{hash_obj.hexdigest()[:6]}"


class Projeto(models.Model):
    """Modelo de Projeto - agregador de boards"""

    nome = models.CharField(max_length=200)
    cliente = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='projetos_criados'
    )
    membros = models.ManyToManyField(
        Usuario,
        related_name='projetos_membro'
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projeto'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} - {self.cliente}"


class Board(models.Model):
    """Quadro Kanban do projeto"""

    titulo = models.CharField(max_length=200)
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='boards'
    )
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'board'
        ordering = ['titulo']

    def __str__(self):
        return f"{self.titulo} ({self.projeto.nome})"

    def criar_colunas_padrao(self):
        """Cria colunas padrão para novo board"""
        colunas_padrao = ['Backlog', 'Em Progresso', 'Em Revisão', 'Concluído']
        for idx, nome in enumerate(colunas_padrao):
            Coluna.objects.create(
                titulo=nome,
                board=self,
                ordem=idx
            )


class Coluna(models.Model):
    """Coluna do board Kanban"""

    titulo = models.CharField(max_length=100)
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='colunas'
    )
    ordem = models.IntegerField(default=0)
    limite_wip = models.IntegerField(
        default=0,
        help_text="Work In Progress - 0 = sem limite"
    )
    cor = models.CharField(max_length=7, default='#6B7280')

    class Meta:
        db_table = 'coluna'
        ordering = ['ordem', 'titulo']
        unique_together = ['board', 'ordem']

    def __str__(self):
        return f"{self.titulo} - {self.board.titulo}"

    def pode_adicionar_item(self):
        """Verifica se pode adicionar item respeitando WIP"""
        if self.limite_wip == 0:
            return True
        return self.items.filter(arquivado=False).count() < self.limite_wip


class ItemBase(models.Model):
    """
    Classe abstrata base para itens do board
    Demonstra ABSTRAÇÃO e será base para HERANÇA
    """

    class Meta:
        abstract = True

    PRIORIDADE_CHOICES = [
        ('baixa', '🟢 Baixa'),
        ('media', '🟡 Média'),
        ('alta', '🟠 Alta'),
        ('critica', '🔴 Crítica'),
    ]

    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    coluna = models.ForeignKey(
        Coluna,
        on_delete=models.CASCADE,
        related_name='%(class)s_items'
    )
    responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_responsavel'
    )
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default='media'
    )
    prazo = models.DateField(null=True, blank=True)
    ordem = models.IntegerField(default=0)
    arquivado = models.BooleanField(default=False)
    criado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='%(class)s_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    @abstractmethod
    def calcular_pontos(self):
        """Método abstrato - deve ser implementado nas subclasses"""
        pass

    @abstractmethod
    def get_tipo_display(self):
        """Retorna o tipo do item para exibição"""
        pass

    def esta_atrasado(self):
        """Verifica se o item está atrasado"""
        if self.prazo and self.coluna.titulo != 'Concluído':
            return timezone.now().date() > self.prazo
        return False

    def mover_para_coluna(self, nova_coluna):
        """Move item para nova coluna"""
        if nova_coluna.pode_adicionar_item():
            self.coluna = nova_coluna
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"


class Bug(ItemBase):
    """
    Modelo de Bug - herda de ItemBase
    Demonstra HERANÇA e POLIMORFISMO
    """

    SEVERIDADE_CHOICES = [
        ('baixa', 'Baixa - Cosmético'),
        ('media', 'Média - Funcional menor'),
        ('alta', 'Alta - Funcional maior'),
        ('critica', 'Crítica - Sistema parado'),
    ]

    severidade = models.CharField(
        max_length=10,
        choices=SEVERIDADE_CHOICES,
        default='media'
    )
    ambiente = models.CharField(
        max_length=50,
        default='produção',
        help_text="Ex: produção, homologação, desenvolvimento"
    )
    passos_reproducao = models.TextField(blank=True)

    class Meta:
        db_table = 'bug'
        ordering = ['-prioridade', '-criado_em']

    def calcular_pontos(self):
        """
        Implementação polimórfica - bugs valem 3 pontos base
        + bônus por severidade
        """
        pontos_base = 3
        bonus_severidade = {
            'baixa': 0,
            'media': 1,
            'alta': 2,
            'critica': 3
        }
        return pontos_base + bonus_severidade.get(self.severidade, 0)

    def get_tipo_display(self):
        """Retorna tipo para display"""
        return "🐛 Bug"

    def get_cor_severidade(self):
        """Retorna cor baseada na severidade"""
        cores = {
            'baixa': '#10B981',  # verde
            'media': '#F59E0B',  # amarelo
            'alta': '#F97316',  # laranja
            'critica': '#EF4444'  # vermelho
        }
        return cores.get(self.severidade, '#6B7280')


class Feature(ItemBase):
    """
    Modelo de Feature - herda de ItemBase
    Demonstra HERANÇA e POLIMORFISMO
    """

    CATEGORIA_CHOICES = [
        ('ux', 'UX/UI'),
        ('backend', 'Backend'),
        ('frontend', 'Frontend'),
        ('infra', 'Infraestrutura'),
        ('docs', 'Documentação'),
    ]

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='backend'
    )
    estimativa_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    especificacao_url = models.URLField(blank=True)

    class Meta:
        db_table = 'feature'
        ordering = ['-prioridade', '-criado_em']

    def calcular_pontos(self):
        """
        Implementação polimórfica - features valem 5 pontos base
        + ajuste por complexidade (baseado em horas)
        """
        pontos_base = 5

        # Ajuste por complexidade baseado em horas estimadas
        if self.estimativa_horas <= 4:
            return pontos_base  # Simples
        elif self.estimativa_horas <= 8:
            return pontos_base + 3  # Médio
        elif self.estimativa_horas <= 16:
            return pontos_base + 5  # Complexo
        else:
            return pontos_base + 8  # Épico

    def get_tipo_display(self):
        """Retorna tipo para display"""
        return "✨ Feature"

    def get_icon_categoria(self):
        """Retorna ícone baseado na categoria"""
        icons = {
            'ux': '🎨',
            'backend': '⚙️',
            'frontend': '🖥️',
            'infra': '🏗️',
            'docs': '📝'
        }
        return icons.get(self.categoria, '📦')


class RegistroHora(models.Model):
    """Registro de horas trabalhadas em items"""

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='registros_hora'
    )

    # Relacionamento genérico para Bug ou Feature
    bug = models.ForeignKey(
        Bug,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='registros_hora'
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='registros_hora'
    )

    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    descricao = models.TextField(blank=True)

    class Meta:
        db_table = 'registro_hora'
        ordering = ['-inicio']

    def __str__(self):
        item = self.bug or self.feature
        return f"{self.usuario.username} - {item.titulo if item else 'N/A'}"

    @property
    def duracao(self):
        """Calcula duração em horas"""
        if self.fim:
            delta = self.fim - self.inicio
            return round(delta.total_seconds() / 3600, 2)
        return 0

    @property
    def item(self):
        """Retorna o item associado (bug ou feature)"""
        return self.bug or self.feature

    def clean(self):
        """Validação: deve ter bug OU feature, não ambos"""
        from django.core.exceptions import ValidationError

        if self.bug and self.feature:
            raise ValidationError("Registro deve ser de Bug OU Feature, não ambos")

        if not self.bug and not self.feature:
            raise ValidationError("Registro deve ter um Bug ou Feature associado")

        if self.fim and self.fim <= self.inicio:
            raise ValidationError("Fim deve ser posterior ao início")


class Comentario(models.Model):
    """Comentários em bugs ou features"""

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='comentarios'
    )

    # Relacionamento genérico
    bug = models.ForeignKey(
        Bug,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comentarios'
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comentarios'
    )

    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    editado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'comentario'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Comentário de {self.usuario.username} em {self.criado_em:%d/%m/%Y}"