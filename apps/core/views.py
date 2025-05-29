# apps/core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Usuario, Projeto, Bug, Feature


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    View de login com suporte a "lembrar-me"
    """
    if request.user.is_authenticated:
        return redirect('painel')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        lembrar_me = request.POST.get('lembrar_me')

        # Autenticar usuário
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Configurar duração da sessão
            if lembrar_me:
                # 30 dias se marcou "lembrar-me"
                request.session.set_expiry(30 * 24 * 60 * 60)
            else:
                # Sessão expira ao fechar o navegador
                request.session.set_expiry(0)

            messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')

            # Redirecionar para próxima página ou painel
            next_url = request.GET.get('next', 'painel')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuário ou senha inválidos.')

    context = {
        'title': 'Login - Vortex Board',
        'next': request.GET.get('next', '')
    }
    return render(request, 'core/login.html', context)


@login_required
def logout_view(request):
    """
    View de logout
    """
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('login')


@login_required
def painel_view(request):
    """
    Painel principal - lista projetos do usuário
    """
    # Obter projetos que o usuário é membro
    projetos = Projeto.objects.filter(
        membros=request.user,
        ativo=True
    ).annotate(
        total_boards=Count('boards'),
        total_bugs=Count('boards__colunas__bug_items', distinct=True),
        total_features=Count('boards__colunas__feature_items', distinct=True)
    ).order_by('-criado_em')

    # Estatísticas gerais do usuário
    stats = {
        'projetos_total': projetos.count(),
        'tarefas_responsavel': 0,
        'tarefas_concluidas': 0,
        'horas_registradas': 0
    }

    # Contar tarefas onde o usuário é responsável
    bugs_responsavel = Bug.objects.filter(
        responsavel=request.user,
        arquivado=False
    )
    features_responsavel = Feature.objects.filter(
        responsavel=request.user,
        arquivado=False
    )

    stats['tarefas_responsavel'] = bugs_responsavel.count() + features_responsavel.count()

    # Contar tarefas concluídas
    stats['tarefas_concluidas'] = (
            bugs_responsavel.filter(coluna__titulo='Concluído').count() +
            features_responsavel.filter(coluna__titulo='Concluído').count()
    )

    # Calcular horas registradas no último mês
    ultimo_mes = timezone.now() - timedelta(days=30)
    registros = request.user.registros_hora.filter(
        inicio__gte=ultimo_mes,
        fim__isnull=False
    )
    stats['horas_registradas'] = sum(r.duracao for r in registros)

    # Tarefas urgentes (vencendo hoje ou atrasadas)
    hoje = timezone.now().date()
    tarefas_urgentes = []

    # Bugs urgentes
    for bug in bugs_responsavel.exclude(coluna__titulo='Concluído'):
        if bug.prazo and bug.prazo <= hoje:
            tarefas_urgentes.append({
                'tipo': 'bug',
                'item': bug,
                'dias_atraso': (hoje - bug.prazo).days if bug.prazo < hoje else 0
            })

    # Features urgentes
    for feature in features_responsavel.exclude(coluna__titulo='Concluído'):
        if feature.prazo and feature.prazo <= hoje:
            tarefas_urgentes.append({
                'tipo': 'feature',
                'item': feature,
                'dias_atraso': (hoje - feature.prazo).days if feature.prazo < hoje else 0
            })

    # Ordenar por dias de atraso
    tarefas_urgentes.sort(key=lambda x: x['dias_atraso'], reverse=True)

    context = {
        'title': 'Painel - Vortex Board',
        'projetos': projetos,
        'stats': stats,
        'tarefas_urgentes': tarefas_urgentes[:5],  # Mostrar apenas 5 mais urgentes
        'pode_criar_projeto': request.user.pode_criar_projeto()
    }

    return render(request, 'core/painel.html', context)


@login_required
def perfil_view(request):
    """
    View do perfil do usuário
    """
    if request.method == 'POST':
        # Atualizar informações básicas
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.telefone = request.POST.get('telefone', '')

        # Processar foto se enviada
        if 'foto' in request.FILES:
            user.foto = request.FILES['foto']

        # Alterar senha se fornecida
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            senha_atual = request.POST.get('senha_atual')
            if user.check_password(senha_atual):
                user.set_password(nova_senha)
                messages.success(request, 'Senha alterada com sucesso!')
                # Re-autenticar após mudança de senha
                login(request, user)
            else:
                messages.error(request, 'Senha atual incorreta.')
                return redirect('perfil')

        user.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('perfil')

    # Estatísticas do perfil
    stats = {
        'projetos': request.user.projetos_membro.count(),
        'tarefas_criadas': (
                Bug.objects.filter(criado_por=request.user).count() +
                Feature.objects.filter(criado_por=request.user).count()
        ),
        'comentarios': request.user.comentarios.count(),
        'horas_total': sum(
            r.duracao for r in request.user.registros_hora.filter(fim__isnull=False)
        )
    }

    # Atividade recente
    atividades = []

    # Últimos comentários
    for comentario in request.user.comentarios.order_by('-criado_em')[:5]:
        atividades.append({
            'tipo': 'comentario',
            'data': comentario.criado_em,
            'descricao': f'Comentou em "{comentario.bug or comentario.feature}"'
        })

    # Últimos registros de hora
    for registro in request.user.registros_hora.order_by('-inicio')[:5]:
        if registro.fim:
            atividades.append({
                'tipo': 'hora',
                'data': registro.inicio,
                'descricao': f'Registrou {registro.duracao:.1f}h em "{registro.item}"'
            })

    # Ordenar atividades por data
    atividades.sort(key=lambda x: x['data'], reverse=True)

    context = {
        'title': 'Meu Perfil - Vortex Board',
        'stats': stats,
        'atividades': atividades[:10]  # Últimas 10 atividades
    }

    return render(request, 'core/perfil.html', context)


@login_required
@require_http_methods(["GET"])
def health_check(request):
    """
    Endpoint de health check para monitoramento
    """
    from django.http import JsonResponse
    from django.db import connection

    try:
        # Verificar conexão com banco
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Verificar Redis se configurado
        redis_ok = True
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 1)
            redis_ok = cache.get('health_check') == 'ok'
        except:
            redis_ok = False

        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'ok',
            'redis': 'ok' if redis_ok else 'unavailable',
            'version': '0.1.0'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)