# apps/core/utils.py

import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from typing import Dict, List, Tuple, Optional


def gerar_cor_usuario(username: str) -> str:
    """
    Gera uma cor consistente baseada no username
    Útil para avatares quando não há foto
    """
    # Gerar hash do username
    hash_obj = hashlib.md5(username.encode())
    hash_hex = hash_obj.hexdigest()

    # Usar primeiros 6 caracteres como cor hex
    return f"#{hash_hex[:6]}"


def formatar_duracao(horas: float) -> str:
    """
    Formata duração em horas para formato legível
    Ex: 2.5 -> "2h 30min"
    """
    if not horas:
        return "0min"

    horas_int = int(horas)
    minutos = int((horas - horas_int) * 60)

    if horas_int == 0:
        return f"{minutos}min"
    elif minutos == 0:
        return f"{horas_int}h"
    else:
        return f"{horas_int}h {minutos}min"


def calcular_velocidade_equipe(projeto, dias: int = 30) -> Dict:
    """
    Calcula métricas de velocidade da equipe
    """
    from .models import Bug, Feature

    data_inicio = timezone.now() - timedelta(days=dias)

    # Items concluídos no período
    bugs_concluidos = Bug.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído',
        atualizado_em__gte=data_inicio
    )

    features_concluidas = Feature.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído',
        atualizado_em__gte=data_inicio
    )

    # Calcular pontos
    pontos_bugs = sum(bug.calcular_pontos() for bug in bugs_concluidos)
    pontos_features = sum(feature.calcular_pontos() for feature in features_concluidas)

    return {
        'periodo_dias': dias,
        'bugs_concluidos': bugs_concluidos.count(),
        'features_concluidas': features_concluidas.count(),
        'total_items': bugs_concluidos.count() + features_concluidas.count(),
        'pontos_bugs': pontos_bugs,
        'pontos_features': pontos_features,
        'pontos_totais': pontos_bugs + pontos_features,
        'velocidade_diaria': (pontos_bugs + pontos_features) / dias
    }


def gerar_burndown_chart_data(board) -> Dict:
    """
    Gera dados para gráfico burndown do sprint
    """
    from .models import Bug, Feature

    # Assumir sprint de 14 dias
    sprint_dias = 14
    data_inicio = timezone.now() - timedelta(days=sprint_dias)

    # Pontos totais no início
    todos_bugs = Bug.objects.filter(coluna__board=board, arquivado=False)
    todas_features = Feature.objects.filter(coluna__board=board, arquivado=False)

    pontos_totais = sum(b.calcular_pontos() for b in todos_bugs)
    pontos_totais += sum(f.calcular_pontos() for f in todas_features)

    # Calcular pontos restantes por dia
    dados_burndown = []
    pontos_restantes = pontos_totais

    for dia in range(sprint_dias + 1):
        data = data_inicio + timedelta(days=dia)

        # Pontos concluídos até esta data
        bugs_concluidos = todos_bugs.filter(
            coluna__titulo='Concluído',
            atualizado_em__date__lte=data.date()
        )
        features_concluidas = todas_features.filter(
            coluna__titulo='Concluído',
            atualizado_em__date__lte=data.date()
        )

        pontos_concluidos = sum(b.calcular_pontos() for b in bugs_concluidos)
        pontos_concluidos += sum(f.calcular_pontos() for f in features_concluidas)

        dados_burndown.append({
            'dia': dia,
            'data': data.strftime('%d/%m'),
            'pontos_restantes': pontos_totais - pontos_concluidos,
            'ideal': pontos_totais - (pontos_totais * dia / sprint_dias)
        })

    return {
        'labels': [d['data'] for d in dados_burndown],
        'real': [d['pontos_restantes'] for d in dados_burndown],
        'ideal': [d['ideal'] for d in dados_burndown],
        'pontos_totais': pontos_totais
    }


def calcular_distribuicao_tarefas(projeto) -> Dict:
    """
    Calcula distribuição de tarefas por membro da equipe
    """
    from .models import Bug, Feature

    membros = projeto.membros.all()
    distribuicao = []

    for membro in membros:
        bugs_resp = Bug.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            arquivado=False
        ).exclude(coluna__titulo='Concluído')

        features_resp = Feature.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            arquivado=False
        ).exclude(coluna__titulo='Concluído')

        distribuicao.append({
            'membro': membro,
            'bugs': bugs_resp.count(),
            'features': features_resp.count(),
            'total': bugs_resp.count() + features_resp.count(),
            'pontos': sum(b.calcular_pontos() for b in bugs_resp) +
                      sum(f.calcular_pontos() for f in features_resp)
        })

    # Ordenar por carga de trabalho (pontos)
    distribuicao.sort(key=lambda x: x['pontos'], reverse=True)

    return {
        'distribuicao': distribuicao,
        'mais_carregado': distribuicao[0] if distribuicao else None,
        'menos_carregado': distribuicao[-1] if distribuicao else None
    }


def verificar_gargalos_wip(board) -> List[Dict]:
    """
    Identifica colunas que estão no limite WIP ou próximas
    """
    gargalos = []

    for coluna in board.colunas.filter(limite_wip__gt=0):
        total_items = (
                coluna.bug_items.filter(arquivado=False).count() +
                coluna.feature_items.filter(arquivado=False).count()
        )

        percentual_uso = (total_items / coluna.limite_wip) * 100

        if percentual_uso >= 80:  # 80% ou mais é considerado gargalo
            gargalos.append({
                'coluna': coluna,
                'items': total_items,
                'limite': coluna.limite_wip,
                'percentual': percentual_uso,
                'status': 'crítico' if percentual_uso >= 100 else 'alerta'
            })

    return gargalos


def gerar_resumo_diario(usuario) -> Dict:
    """
    Gera resumo diário personalizado para o usuário
    """
    from .models import Bug, Feature, RegistroHora, Comentario

    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)

    # Tarefas do usuário
    bugs_abertos = Bug.objects.filter(
        responsavel=usuario,
        arquivado=False
    ).exclude(coluna__titulo='Concluído')

    features_abertas = Feature.objects.filter(
        responsavel=usuario,
        arquivado=False
    ).exclude(coluna__titulo='Concluído')

    # Vencimentos
    vencendo_hoje = []
    atrasadas = []

    for item in list(bugs_abertos) + list(features_abertas):
        if item.prazo:
            if item.prazo == hoje:
                vencendo_hoje.append(item)
            elif item.prazo < hoje:
                atrasadas.append(item)

    # Atividade de ontem
    horas_ontem = RegistroHora.objects.filter(
        usuario=usuario,
        inicio__date=ontem,
        fim__isnull=False
    ).aggregate(total=Sum('duracao'))['total'] or 0

    comentarios_ontem = Comentario.objects.filter(
        usuario=usuario,
        criado_em__date=ontem
    ).count()

    return {
        'bugs_abertos': bugs_abertos.count(),
        'features_abertas': features_abertas.count(),
        'total_tarefas': bugs_abertos.count() + features_abertas.count(),
        'vencendo_hoje': len(vencendo_hoje),
        'atrasadas': len(atrasadas),
        'horas_ontem': horas_ontem,
        'comentarios_ontem': comentarios_ontem,
        'tarefas_prioritarias': sorted(
            list(bugs_abertos.filter(prioridade__in=['alta', 'critica'])) +
            list(features_abertas.filter(prioridade__in=['alta', 'critica'])),
            key=lambda x: x.prazo or timezone.now().date() + timedelta(days=365)
        )[:5]
    }


def exportar_metricas_projeto(projeto) -> Dict:
    """
    Exporta métricas completas do projeto para relatórios
    """
    from .models import Bug, Feature, RegistroHora

    # Período de análise
    inicio = projeto.criado_em
    fim = timezone.now()
    duracao_dias = (fim - inicio).days

    # Totais
    total_bugs = Bug.objects.filter(coluna__board__projeto=projeto).count()
    total_features = Feature.objects.filter(coluna__board__projeto=projeto).count()

    # Concluídos
    bugs_concluidos = Bug.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído'
    ).count()

    features_concluidas = Feature.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído'
    ).count()

    # Horas trabalhadas
    horas_totais = RegistroHora.objects.filter(
        Q(bug__coluna__board__projeto=projeto) |
        Q(feature__coluna__board__projeto=projeto),
        fim__isnull=False
    ).aggregate(total=Sum('duracao'))['total'] or 0

    # Métricas por membro
    metricas_membros = []
    for membro in projeto.membros.all():
        horas_membro = RegistroHora.objects.filter(
            usuario=membro,
            Q(bug__coluna__board__projeto=projeto) |
            Q(feature__coluna__board__projeto=projeto),
            fim__isnull=False
        ).aggregate(total=Sum('duracao'))['total'] or 0

        metricas_membros.append({
            'membro': membro.get_full_name() or membro.username,
            'horas': horas_membro,
            'percentual': (horas_membro / horas_totais * 100) if horas_totais > 0 else 0
        })

    return {
        'projeto': projeto.nome,
        'cliente': projeto.cliente,
        'duracao_dias': duracao_dias,
        'membros_total': projeto.membros.count(),
        'bugs': {
            'total': total_bugs,
            'concluidos': bugs_concluidos,
            'percentual': (bugs_concluidos / total_bugs * 100) if total_bugs > 0 else 0
        },
        'features': {
            'total': total_features,
            'concluidas': features_concluidas,
            'percentual': (features_concluidas / total_features * 100) if total_features > 0 else 0
        },
        'horas_totais': horas_totais,
        'metricas_membros': metricas_membros,
        'velocidade_media': calcular_velocidade_equipe(projeto, 30)
    }