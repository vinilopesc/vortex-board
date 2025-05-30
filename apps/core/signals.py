# apps/core/signals.py

from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from .models import Usuario, Projeto, Board, Bug, Feature, RegistroHora


@receiver(post_save, sender=Board)
def criar_colunas_padrao(sender, instance, created, **kwargs):
    """
    Cria colunas padrão quando um novo board é criado
    APENAS se não há colunas e não está sendo criado via seed
    """
    if created and not instance.colunas.exists():
        # Verificar se é criação via seed (pode ter flag especial)
        # Por padrão, criar colunas simples sem customização
        instance.criar_colunas_padrao()


@receiver(pre_save, sender=RegistroHora)
def calcular_duracao_automatica(sender, instance, **kwargs):
    """
    Calcula duração automaticamente quando fim é definido
    """
    if instance.fim and instance.inicio and not instance.pk:
        # Apenas para novos registros
        delta = instance.fim - instance.inicio
        if delta.total_seconds() < 0:
            instance.fim = None  # Resetar se fim for antes do início


@receiver(m2m_changed, sender=Projeto.membros.through)
def notificar_novos_membros(sender, instance, action, pk_set, **kwargs):
    """
    Notifica quando novos membros são adicionados ao projeto
    (Placeholder para futuras notificações)
    """
    if action == "post_add" and pk_set:
        # TODO: Implementar sistema de notificações
        # Por enquanto, apenas log
        novos_membros = Usuario.objects.filter(pk__in=pk_set)
        for membro in novos_membros:
            print(f"[NOTIFICAÇÃO] {membro.username} foi adicionado ao projeto {instance.nome}")


@receiver(pre_save, sender=Bug)
@receiver(pre_save, sender=Feature)
def atualizar_timestamp_coluna(sender, instance, **kwargs):
    """
    Atualiza timestamp quando item muda de coluna
    """
    if instance.pk:  # Apenas para updates
        try:
            obj_anterior = sender.objects.get(pk=instance.pk)
            if obj_anterior.coluna_id != instance.coluna_id:
                # Item mudou de coluna
                instance.atualizado_em = timezone.now()

                # Se movendo para "Concluído", registrar
                if instance.coluna.titulo == 'Concluído' and obj_anterior.coluna.titulo != 'Concluído':
                    print(f"[LOG] {instance.get_tipo_display()} '{instance.titulo}' foi concluído!")

        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=Usuario)
def criar_projeto_pessoal(sender, instance, created, **kwargs):
    """
    Cria projeto pessoal para novos usuários gerentes/admin
    (Opcional - comentado por padrão)
    """
    # if created and instance.tipo in ['admin', 'gerente']:
    #     projeto = Projeto.objects.create(
    #         nome=f"Projeto Pessoal - {instance.get_full_name() or instance.username}",
    #         cliente="Interno",
    #         descricao="Projeto pessoal para organização de tarefas",
    #         criado_por=instance
    #     )
    #     projeto.membros.add(instance)
    pass


# Handlers para manter integridade referencial

@receiver(pre_save, sender=Bug)
@receiver(pre_save, sender=Feature)
def validar_responsavel_membro(sender, instance, **kwargs):
    """
    Garante que o responsável seja membro do projeto
    """
    if instance.responsavel and instance.coluna_id:
        projeto = instance.coluna.board.projeto
        if instance.responsavel not in projeto.membros.all():
            # Adicionar automaticamente ou lançar erro
            projeto.membros.add(instance.responsavel)
            print(f"[AUTO] {instance.responsavel.username} adicionado ao projeto {projeto.nome}")