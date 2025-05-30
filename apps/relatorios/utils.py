# apps/relatorios/utils.py

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg
from typing import Dict, List, Tuple
import json

from apps.core.models import Bug, Feature, RegistroHora, Projeto


def gerar_dados_burndown_avancado(projeto: Projeto, dias: int = 14) -> Dict:
    """
    Gera dados avançados para gráfico burndown
    Inclui linha ideal vs realizada com projeções
    """
    data_inicio = timezone.now() - timedelta(days=dias)

    # Pontos totais no início do período
    bugs = Bug.objects.filter(coluna__board__projeto=projeto, arquivado=False)
    features = Feature.objects.filter(coluna__board__projeto=projeto, arquivado=False)

    pontos_totais = sum(b.calcular_pontos() for b in bugs)
    pontos_totais += sum(f.calcular_pontos() for f in features)

    # Dados por dia
    dados_burndown = []
    pontos_acumulados_concluidos = 0

    for dia in range(dias + 1):
        data_atual = data_inicio + timedelta(days=dia)

        # Pontos concluídos até esta data
        bugs_concluidos_dia = bugs.filter(
            coluna__titulo='Concluído',
            atualizado_em__date=data_atual.date()
        )
        features_concluidas_dia = features.filter(
            coluna__titulo='Concluído',
            atualizado_em__date=data_atual.date()
        )

        pontos_dia = sum(b.calcular_pontos() for b in bugs_concluidos_dia)
        pontos_dia += sum(f.calcular_pontos() for f in features_concluidas_dia)

        pontos_acumulados_concluidos += pontos_dia
        pontos_restantes = pontos_totais - pontos_acumulados_concluidos

        # Linha ideal (linear)
        pontos_ideal = pontos_totais - (pontos_totais * dia / dias)

        dados_burndown.append({
            'dia': dia,
            'data': data_atual.strftime('%d/%m'),
            'pontos_restantes': max(0, pontos_restantes),
            'pontos_ideal': max(0, pontos_ideal),
            'pontos_concluidos_dia': pontos_dia,
            'velocidade_media': pontos_acumulados_concluidos / max(1, dia) if dia > 0 else 0
        })

    # Projeção baseada na velocidade atual
    velocidade_atual = pontos_acumulados_concluidos / max(1, dias)
    dias_para_conclusao = int(pontos_restantes / max(1, velocidade_atual)) if velocidade_atual > 0 else float('inf')

    return {
        'dados': dados_burndown,
        'pontos_totais': pontos_totais,
        'pontos_concluidos': pontos_acumulados_concluidos,
        'pontos_restantes': pontos_restantes,
        'velocidade_atual': round(velocidade_atual, 2),
        'dias_para_conclusao': dias_para_conclusao,
        'status': 'no_prazo' if dias_para_conclusao <= (dias - len(dados_burndown)) else 'atrasado'
    }


def calcular_metricas_produtividade(projeto: Projeto, periodo_dias: int = 30) -> Dict:
    """
    Calcula métricas avançadas de produtividade da equipe
    """
    data_inicio = timezone.now() - timedelta(days=periodo_dias)

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

    # Tempo médio de resolução
    tempo_resolucao_bugs = []
    tempo_resolucao_features = []

    for bug in bugs_concluidos:
        delta = bug.atualizado_em - bug.criado_em
        tempo_resolucao_bugs.append(delta.days)

    for feature in features_concluidas:
        delta = feature.atualizado_em - feature.criado_em
        tempo_resolucao_features.append(delta.days)

    # Calcular médias
    tempo_medio_bugs = sum(tempo_resolucao_bugs) / len(tempo_resolucao_bugs) if tempo_resolucao_bugs else 0
    tempo_medio_features = sum(tempo_resolucao_features) / len(
        tempo_resolucao_features) if tempo_resolucao_features else 0

    # Pontos entregues
    pontos_bugs = sum(bug.calcular_pontos() for bug in bugs_concluidos)
    pontos_features = sum(feature.calcular_pontos() for feature in features_concluidas)

    # Throughput (items por dia)
    throughput_bugs = len(bugs_concluidos) / periodo_dias
    throughput_features = len(features_concluidas) / periodo_dias

    # Distribuição por prioridade
    distribuicao_prioridade = {}
    for prioridade in ['baixa', 'media', 'alta', 'critica']:
        count = (
                bugs_concluidos.filter(prioridade=prioridade).count() +
                features_concluidas.filter(prioridade=prioridade).count()
        )
        distribuicao_prioridade[prioridade] = count

    return {
        'periodo_dias': periodo_dias,
        'bugs_concluidos': len(bugs_concluidos),
        'features_concluidas': len(features_concluidas),
        'total_items': len(bugs_concluidos) + len(features_concluidas),
        'pontos_totais': pontos_bugs + pontos_features,
        'velocidade_diaria': (pontos_bugs + pontos_features) / periodo_dias,
        'tempo_medio_resolucao': {
            'bugs': round(tempo_medio_bugs, 1),
            'features': round(tempo_medio_features, 1),
            'geral': round((tempo_medio_bugs + tempo_medio_features) / 2,
                           1) if tempo_medio_bugs > 0 or tempo_medio_features > 0 else 0
        },
        'throughput': {
            'bugs_por_dia': round(throughput_bugs, 2),
            'features_por_dia': round(throughput_features, 2),
            'items_por_dia': round(throughput_bugs + throughput_features, 2)
        },
        'distribuicao_prioridade': distribuicao_prioridade
    }
# CONTINUAÇÃO do apps/relatorios/utils.py - PARTE 2

def gerar_grafico_velocidade(projeto: Projeto, sprints: int = 5) -> Dict:
    """
    Gera dados para gráfico de velocidade por sprint
    Assume sprints de 14 dias
    """
    dados_sprints = []
    dias_por_sprint = 14

    for sprint_num in range(sprints):
        # Calcular período do sprint
        fim_sprint = timezone.now() - timedelta(days=sprint_num * dias_por_sprint)
        inicio_sprint = fim_sprint - timedelta(days=dias_por_sprint)

        # Items concluídos neste sprint
        bugs_sprint = Bug.objects.filter(
            coluna__board__projeto=projeto,
            coluna__titulo='Concluído',
            atualizado_em__range=[inicio_sprint, fim_sprint]
        )

        features_sprint = Feature.objects.filter(
            coluna__board__projeto=projeto,
            coluna__titulo='Concluído',
            atualizado_em__range=[inicio_sprint, fim_sprint]
        )

        # Calcular pontos
        pontos_bugs = sum(bug.calcular_pontos() for bug in bugs_sprint)
        pontos_features = sum(feature.calcular_pontos() for feature in features_sprint)
        pontos_totais = pontos_bugs + pontos_features

        dados_sprints.append({
            'sprint': f"Sprint {sprints - sprint_num}",
            'inicio': inicio_sprint.strftime('%d/%m'),
            'fim': fim_sprint.strftime('%d/%m'),
            'pontos_bugs': pontos_bugs,
            'pontos_features': pontos_features,
            'pontos_totais': pontos_totais,
            'items_total': len(bugs_sprint) + len(features_sprint)
        })

    # Reverter para ordem cronológica
    dados_sprints.reverse()

    # Calcular tendência
    pontos_sprints = [s['pontos_totais'] for s in dados_sprints]
    velocidade_media = sum(pontos_sprints) / len(pontos_sprints) if pontos_sprints else 0

    # Tendência simples (últimos 3 vs primeiros 2)
    if len(pontos_sprints) >= 3:
        ultimos_3 = sum(pontos_sprints[-3:]) / 3
        primeiros_2 = sum(pontos_sprints[:2]) / 2 if len(pontos_sprints) >= 2 else pontos_sprints[0]
        tendencia = 'crescente' if ultimos_3 > primeiros_2 else 'decrescente' if ultimos_3 < primeiros_2 else 'estavel'
    else:
        tendencia = 'indefinida'

    return {
        'sprints': dados_sprints,
        'velocidade_media': round(velocidade_media, 1),
        'tendencia': tendencia,
        'melhor_sprint': max(dados_sprints, key=lambda x: x['pontos_totais']) if dados_sprints else None,
        'pior_sprint': min(dados_sprints, key=lambda x: x['pontos_totais']) if dados_sprints else None
    }


def calcular_distribuicao_trabalho(projeto: Projeto) -> Dict:
    """
    Calcula distribuição detalhada de trabalho por membro
    """
    membros_dados = []

    for membro in projeto.membros.all():
        # Tarefas ativas
        bugs_ativos = Bug.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            arquivado=False
        ).exclude(coluna__titulo='Concluído')

        features_ativas = Feature.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            arquivado=False
        ).exclude(coluna__titulo='Concluído')

        # Tarefas concluídas (último mês)
        ultimo_mes = timezone.now() - timedelta(days=30)
        bugs_concluidos = Bug.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            coluna__titulo='Concluído',
            atualizado_em__gte=ultimo_mes
        )

        features_concluidas = Feature.objects.filter(
            responsavel=membro,
            coluna__board__projeto=projeto,
            coluna__titulo='Concluído',
            atualizado_em__gte=ultimo_mes
        )

        # Horas trabalhadas (último mês) - CORRIGIDO
        horas_trabalhadas = RegistroHora.objects.filter(
            usuario=membro,
            inicio__gte=ultimo_mes,
            fim__isnull=False
        ).filter(
            Q(bug__coluna__board__projeto=projeto) | Q(feature__coluna__board__projeto=projeto)
        ).aggregate(total=Sum('duracao'))['total'] or 0

        # Calcular pontos
        pontos_ativos = sum(b.calcular_pontos() for b in bugs_ativos) + sum(
            f.calcular_pontos() for f in features_ativas)
        pontos_concluidos = sum(b.calcular_pontos() for b in bugs_concluidos) + sum(
            f.calcular_pontos() for f in features_concluidas)

        # Distribuição por prioridade (tarefas ativas)
        prioridades = {'critica': 0, 'alta': 0, 'media': 0, 'baixa': 0}
        for bug in bugs_ativos:
            prioridades[bug.prioridade] += 1
        for feature in features_ativas:
            prioridades[feature.prioridade] += 1

        membros_dados.append({
            'membro': membro,
            'nome': membro.get_full_name() or membro.username,
            'tarefas_ativas': {
                'bugs': len(bugs_ativos),
                'features': len(features_ativas),
                'total': len(bugs_ativos) + len(features_ativas)
            },
            'tarefas_concluidas_mes': {
                'bugs': len(bugs_concluidos),
                'features': len(features_concluidas),
                'total': len(bugs_concluidos) + len(features_concluidas)
            },
            'pontos': {
                'ativos': pontos_ativos,
                'concluidos_mes': pontos_concluidos
            },
            'horas_trabalhadas_mes': float(horas_trabalhadas),
            'produtividade': round(pontos_concluidos / max(1, horas_trabalhadas), 2) if horas_trabalhadas > 0 else 0,
            'distribuicao_prioridade': prioridades
        })

    # Ordenar por carga de trabalho (pontos ativos)
    membros_dados.sort(key=lambda x: x['pontos']['ativos'], reverse=True)

    # Estatísticas gerais
    total_pontos_ativos = sum(m['pontos']['ativos'] for m in membros_dados)
    total_horas_mes = sum(m['horas_trabalhadas_mes'] for m in membros_dados)

    return {
        'membros': membros_dados,
        'estatisticas': {
            'total_membros': len(membros_dados),
            'total_pontos_ativos': total_pontos_ativos,
            'total_horas_mes': total_horas_mes,
            'pontos_por_membro': round(total_pontos_ativos / max(1, len(membros_dados)), 1),
            'horas_por_membro': round(total_horas_mes / max(1, len(membros_dados)), 1)
        },
        'desequilibrios': [
            m for m in membros_dados
            if m['pontos']['ativos'] > total_pontos_ativos / len(membros_dados) * 1.5
        ] if membros_dados else []
    }
# CONTINUAÇÃO do apps/relatorios/utils.py - PARTE 3 FINAL

def gerar_relatorio_semanal_automatico(projeto: Projeto) -> Dict:
    """
    Gera relatório semanal automático para envio por email
    """
    # Período: última semana
    fim_semana = timezone.now()
    inicio_semana = fim_semana - timedelta(days=7)

    # Items criados na semana
    bugs_novos = Bug.objects.filter(
        coluna__board__projeto=projeto,
        criado_em__range=[inicio_semana, fim_semana]
    )

    features_novas = Feature.objects.filter(
        coluna__board__projeto=projeto,
        criado_em__range=[inicio_semana, fim_semana]
    )

    # Items concluídos na semana
    bugs_concluidos = Bug.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído',
        atualizado_em__range=[inicio_semana, fim_semana]
    )

    features_concluidas = Feature.objects.filter(
        coluna__board__projeto=projeto,
        coluna__titulo='Concluído',
        atualizado_em__range=[inicio_semana, fim_semana]
    )

    # Horas trabalhadas - CORRIGIDO
    horas_semana = RegistroHora.objects.filter(
        inicio__range=[inicio_semana, fim_semana],
        fim__isnull=False
    ).filter(
        Q(bug__coluna__board__projeto=projeto) | Q(feature__coluna__board__projeto=projeto)
    ).aggregate(total=Sum('duracao'))['total'] or 0

    # Top contributors - CORRIGIDO
    contribuidores = {}
    for registro in RegistroHora.objects.filter(
            inicio__range=[inicio_semana, fim_semana],
            fim__isnull=False
    ).filter(
        Q(bug__coluna__board__projeto=projeto) | Q(feature__coluna__board__projeto=projeto)
    ).select_related('usuario'):
        user_id = registro.usuario.id
        if user_id not in contribuidores:
            contribuidores[user_id] = {
                'usuario': registro.usuario,
                'horas': 0
            }
        contribuidores[user_id]['horas'] += registro.duracao

    top_contribuidores = sorted(
        contribuidores.values(),
        key=lambda x: x['horas'],
        reverse=True
    )[:3]

    return {
        'projeto': projeto.nome,
        'cliente': projeto.cliente,
        'periodo': {
            'inicio': inicio_semana.strftime('%d/%m/%Y'),
            'fim': fim_semana.strftime('%d/%m/%Y')
        },
        'novos_items': {
            'bugs': len(bugs_novos),
            'features': len(features_novas),
            'total': len(bugs_novos) + len(features_novas)
        },
        'items_concluidos': {
            'bugs': len(bugs_concluidos),
            'features': len(features_concluidas),
            'total': len(bugs_concluidos) + len(features_concluidas)
        },
        'pontos_concluidos': sum(b.calcular_pontos() for b in bugs_concluidos) + sum(
            f.calcular_pontos() for f in features_concluidas),
        'horas_trabalhadas': float(horas_semana),
        'top_contribuidores': [
            {
                'nome': c['usuario'].get_full_name() or c['usuario'].username,
                'horas': round(c['horas'], 1)
            }
            for c in top_contribuidores
        ],
        'gerado_em': timezone.now().strftime('%d/%m/%Y %H:%M')
    }