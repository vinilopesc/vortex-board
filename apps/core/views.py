# apps/core/views.py

from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from django.core.paginator import Paginator

from .models import Usuario, Projeto, Board, Bug, Feature, RegistroHora
from .permissions import VortexPermissions


def login_view(request):
    """
    View de login do sistema
    """
    if request.user.is_authenticated:
        return redirect('core:painel')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')
            return redirect('core:painel')
        else:
            messages.error(request, 'Credenciais inválidas. Tente novamente.')

    return render(request, 'core/login.html', {
        'title': 'Login - Vortex Board'
    })


def logout_view(request):
    """
    View de logout
    """
    logout(request)
    messages.info(request, 'Você foi desconectado com sucesso.')
    return redirect('core:login')


@login_required
def painel_principal(request):
    """
    Painel principal do usuário
    Dashboard com projetos, estatísticas e ações rápidas
    """
    # Projetos que o usuário tem acesso
    if request.user.tipo == 'admin':
        projetos = Projeto.objects.filter(ativo=True)
    else:
        projetos = Projeto.objects.filter(
            membros=request.user,
            ativo=True
        ).distinct()

    # Calcular estatísticas de cada projeto
    for projeto in projetos:
        # Total de tarefas
        bugs_projeto = Bug.objects.filter(coluna__board__projeto=projeto)
        features_projeto = Feature.objects.filter(coluna__board__projeto=projeto)

        projeto.total_tarefas = bugs_projeto.count() + features_projeto.count()
        projeto.tarefas_concluidas = (
                bugs_projeto.filter(coluna__titulo='Concluído').count() +
                features_projeto.filter(coluna__titulo='Concluído').count()
        )
        projeto.bugs_abertos = bugs_projeto.exclude(coluna__titulo='Concluído').count()

        # Calcular progresso percentual
        if projeto.total_tarefas > 0:
            projeto.progresso_percentual = (projeto.tarefas_concluidas / projeto.total_tarefas) * 100
        else:
            projeto.progresso_percentual = 0

    # Estatísticas gerais do usuário
    stats = calcular_estatisticas_usuario(request.user, projetos)

    # Tarefas urgentes do usuário
    tarefas_urgentes = obter_tarefas_urgentes(request.user, projetos)

    # Atividades recentes
    atividades_recentes = obter_atividades_recentes(request.user, projetos)

    # Notificações (placeholder)
    notificacoes = []  # TODO: Implementar sistema de notificações
    notificacoes_nao_lidas = 0

    context = {
        'title': 'Painel Principal',
        'projetos': projetos[:10],  # Limitar a 10 projetos na tela
        'stats': stats,
        'tarefas_urgentes': tarefas_urgentes,
        'atividades_recentes': atividades_recentes,
        'notificacoes': notificacoes,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
    }

    return render(request, 'core/painel.html', context)


def calcular_estatisticas_usuario(usuario, projetos):
    """
    Calcula estatísticas do usuário para o dashboard
    """
    # Semana atual
    inicio_semana = timezone.now() - timedelta(days=7)

    # Minhas tarefas (bugs + features)
    minhas_tarefas = (
            Bug.objects.filter(
                responsavel=usuario,
                coluna__board__projeto__in=projetos
            ).exclude(coluna__titulo='Concluído').count() +
            Feature.objects.filter(
                responsavel=usuario,
                coluna__board__projeto__in=projetos
            ).exclude(coluna__titulo='Concluído').count()
    )

    # Tarefas concluídas
    tarefas_concluidas = (
            Bug.objects.filter(
                responsavel=usuario,
                coluna__board__projeto__in=projetos,
                coluna__titulo='Concluído'
            ).count() +
            Feature.objects.filter(
                responsavel=usuario,
                coluna__board__projeto__in=projetos,
                coluna__titulo='Concluído'
            ).count()
    )

    # Bugs ativos
    bugs_ativos = Bug.objects.filter(
        coluna__board__projeto__in=projetos
    ).exclude(coluna__titulo='Concluído').count()

    # Bugs críticos
    bugs_criticos = Bug.objects.filter(
        coluna__board__projeto__in=projetos,
        severidade='critica'
    ).exclude(coluna__titulo='Concluído').count()

    # Horas trabalhadas na semana
    registros_semana = RegistroHora.objects.filter(
        usuario=usuario,
        inicio__gte=inicio_semana,
        fim__isnull=False
    ).filter(
        Q(bug__coluna__board__projeto__in=projetos) |
        Q(feature__coluna__board__projeto__in=projetos)
    )

    horas_semana = sum(registro.duracao for registro in registros_semana)

    # Tarefas concluídas na semana
    tarefas_concluidas_semana = (
            Bug.objects.filter(
                responsavel=usuario,
                coluna__titulo='Concluído',
                atualizado_em__gte=inicio_semana,
                coluna__board__projeto__in=projetos
            ).count() +
            Feature.objects.filter(
                responsavel=usuario,
                coluna__titulo='Concluído',
                atualizado_em__gte=inicio_semana,
                coluna__board__projeto__in=projetos
            ).count()
    )

    return {
        'projetos_ativos': projetos.count(),
        'minhas_tarefas': minhas_tarefas,
        'tarefas_concluidas': tarefas_concluidas,
        'bugs_ativos': bugs_ativos,
        'bugs_criticos': bugs_criticos,
        'horas_semana': horas_semana,
        'tarefas_concluidas_semana': tarefas_concluidas_semana,
        'meta_semanal': 5,  # Meta de 5 tarefas por semana
    }


def obter_tarefas_urgentes(usuario, projetos):
    """
    Retorna tarefas urgentes do usuário
    """
    hoje = timezone.now().date()
    uma_semana = hoje + timedelta(days=7)

    # Bugs urgentes (críticos ou com prazo próximo)
    bugs_urgentes = Bug.objects.filter(
        responsavel=usuario,
        coluna__board__projeto__in=projetos
    ).exclude(coluna__titulo='Concluído').filter(
        Q(severidade='critica') |
        Q(prioridade='critica') |
        Q(prazo__lte=uma_semana, prazo__isnull=False)
    ).order_by('prazo', '-prioridade')[:5]

    # Features urgentes (alta prioridade ou prazo próximo)
    features_urgentes = Feature.objects.filter(
        responsavel=usuario,
        coluna__board__projeto__in=projetos
    ).exclude(coluna__titulo='Concluído').filter(
        Q(prioridade__in=['critica', 'alta']) |
        Q(prazo__lte=uma_semana, prazo__isnull=False)
    ).order_by('prazo', '-prioridade')[:5]

    # Combinar e ordenar
    tarefas_urgentes = []

    for bug in bugs_urgentes:
        tarefas_urgentes.append({
            'id': bug.id,
            'titulo': bug.titulo,
            'prioridade': bug.prioridade,
            'prazo': bug.prazo,
            'bug': bug,
            'tipo': 'bug'
        })

    for feature in features_urgentes:
        tarefas_urgentes.append({
            'id': feature.id,
            'titulo': feature.titulo,
            'prioridade': feature.prioridade,
            'prazo': feature.prazo,
            'feature': feature,
            'tipo': 'feature'
        })

    # Ordenar por prioridade e prazo
    tarefas_urgentes.sort(key=lambda x: (
        x['prazo'] if x['prazo'] else timezone.now().date() + timedelta(days=999),
        {'critica': 0, 'alta': 1, 'media': 2, 'baixa': 3}.get(x['prioridade'], 4)
    ))

    return tarefas_urgentes[:8]


def obter_atividades_recentes(usuario, projetos):
    """
    Retorna atividades recentes relacionadas aos projetos do usuário
    """
    limite_dias = 7
    data_limite = timezone.now() - timedelta(days=limite_dias)

    atividades = []

    # Bugs criados recentemente
    bugs_recentes = Bug.objects.filter(
        coluna__board__projeto__in=projetos,
        criado_em__gte=data_limite
    ).order_by('-criado_em')[:5]

    for bug in bugs_recentes:
        atividades.append({
            'descricao': f'🐛 Bug "{bug.titulo}" criado por {bug.criado_por.get_full_name() or bug.criado_por.username}',
            'quando': bug.criado_em,
            'tipo': 'bug_criado'
        })

    # Features criadas recentemente
    features_recentes = Feature.objects.filter(
        coluna__board__projeto__in=projetos,
        criado_em__gte=data_limite
    ).order_by('-criado_em')[:5]

    for feature in features_recentes:
        atividades.append({
            'descricao': f'✨ Feature "{feature.titulo}" criada por {feature.criado_por.get_full_name() or feature.criado_por.username}',
            'quando': feature.criado_em,
            'tipo': 'feature_criada'
        })

    # Tarefas concluídas recentemente
    bugs_concluidos = Bug.objects.filter(
        coluna__board__projeto__in=projetos,
        coluna__titulo='Concluído',
        atualizado_em__gte=data_limite
    ).order_by('-atualizado_em')[:3]

    for bug in bugs_concluidos:
        atividades.append({
            'descricao': f'✅ Bug "{bug.titulo}" concluído por {bug.responsavel.get_full_name() if bug.responsavel else "alguém"}',
            'quando': bug.atualizado_em,
            'tipo': 'bug_concluido'
        })

    features_concluidas = Feature.objects.filter(
        coluna__board__projeto__in=projetos,
        coluna__titulo='Concluído',
        atualizado_em__gte=data_limite
    ).order_by('-atualizado_em')[:3]

    for feature in features_concluidas:
        atividades.append({
            'descricao': f'🎉 Feature "{feature.titulo}" concluída por {feature.responsavel.get_full_name() if feature.responsavel else "alguém"}',
            'quando': feature.atualizado_em,
            'tipo': 'feature_concluida'
        })

    # Ordenar por data e limitar
    atividades.sort(key=lambda x: x['quando'], reverse=True)
    return atividades[:10]


@login_required
def perfil_usuario(request):
    """
    Página de perfil do usuário
    """
    if request.method == 'POST':
        # Atualizar perfil
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.telefone = request.POST.get('telefone', '')

        # Verificar se houve upload de foto
        if 'foto' in request.FILES:
            user.foto = request.FILES['foto']

        try:
            user.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar perfil: {str(e)}')

        return redirect('core:perfil')

    context = {
        'title': 'Meu Perfil',
        'user': request.user
    }

    return render(request, 'core/perfil.html', context)


@login_required
def health_check(request):
    """
    Health check para monitoramento
    """
    try:
        # Verificar conexão com banco
        Usuario.objects.count()

        # Verificar Redis se configurado
        from django.core.cache import cache
        cache.set('health_check', 'ok', 60)
        cache.get('health_check')

        status = {
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
            'timestamp': timezone.now().isoformat(),
            'version': '0.1.0'
        }

        return JsonResponse(status)

    except Exception as e:
        status = {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
            'version': '0.1.0'
        }

        return JsonResponse(status, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def criar_projeto(request):
    """
    Criar novo projeto (apenas gerentes e admins)
    """
    if not VortexPermissions.is_gerente_ou_admin(request.user):
        messages.error(request, 'Sem permissão para criar projetos.')
        return redirect('core:painel')

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        cliente = request.POST.get('cliente', '').strip()
        descricao = request.POST.get('descricao', '').strip()

        if not nome or not cliente:
            messages.error(request, 'Nome e cliente são obrigatórios.')
            return redirect('core:painel')

        try:
            # Criar projeto
            projeto = Projeto.objects.create(
                nome=nome,
                cliente=cliente,
                descricao=descricao,
                criado_por=request.user
            )

            # Adicionar criador como membro
            projeto.membros.add(request.user)

            messages.success(request, f'Projeto "{nome}" criado com sucesso!')

            # Redirecionar para o board criado automaticamente
            board = projeto.boards.first()
            if board:
                return redirect('board:kanban', board_id=board.id)
            else:
                return redirect('core:painel')

        except Exception as e:
            messages.error(request, f'Erro ao criar projeto: {str(e)}')

    return redirect('core:painel')


# API endpoints para AJAX
@login_required
def api_estatisticas_painel(request):
    """
    API para atualizar estatísticas do painel via AJAX
    """
    # Projetos do usuário
    if request.user.tipo == 'admin':
        projetos = Projeto.objects.filter(ativo=True)
    else:
        projetos = Projeto.objects.filter(membros=request.user, ativo=True)

    # Calcular estatísticas
    stats = calcular_estatisticas_usuario(request.user, projetos)

    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })


@login_required
def api_tarefas_urgentes(request):
    """
    API para buscar tarefas urgentes via AJAX
    """
    if request.user.tipo == 'admin':
        projetos = Projeto.objects.filter(ativo=True)
    else:
        projetos = Projeto.objects.filter(membros=request.user, ativo=True)

    tarefas = obter_tarefas_urgentes(request.user, projetos)

    return JsonResponse({
        'success': True,
        'tarefas': tarefas,
        'count': len(tarefas)
    })