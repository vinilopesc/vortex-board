# apps/board/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from apps.core.models import Board, Bug, Feature, Coluna, Comentario, RegistroHora
from apps.core.permissions import (
    requer_acesso_board,
    VortexPermissions,
    ajax_requer_permissao
)


@login_required
@requer_acesso_board
def board_kanban_view(request, board_id):
    """
    View principal do Kanban Board
    Carrega colunas com items em tempo real
    """
    board = request.board  # Injetado pelo decorator

    # Prefetch otimizado para evitar N+1 queries
    colunas = board.colunas.prefetch_related(
        Prefetch('bug_items',
                 queryset=Bug.objects.select_related('responsavel').filter(arquivado=False).order_by('ordem')),
        Prefetch('feature_items',
                 queryset=Feature.objects.select_related('responsavel').filter(arquivado=False).order_by('ordem'))
    ).order_by('ordem')

    # Calcular status WIP para cada coluna
    for coluna in colunas:
        total_items = coluna.bug_items.count() + coluna.feature_items.count()
        coluna.total_items = total_items

        # Definir classe CSS baseada no WIP limit
        coluna.wip_status = 'normal'
        if coluna.limite_wip > 0:
            wip_threshold_80 = int(coluna.limite_wip * 0.8)

            if total_items >= coluna.limite_wip:
                coluna.wip_status = 'danger'
            elif total_items >= wip_threshold_80:
                coluna.wip_status = 'warning'

    # Estatísticas do board
    stats = {
        'total_bugs': Bug.objects.filter(coluna__board=board, arquivado=False).count(),
        'total_features': Feature.objects.filter(coluna__board=board, arquivado=False).count(),
        'bugs_concluidos': Bug.objects.filter(coluna__board=board, coluna__titulo='Concluído', arquivado=False).count(),
        'features_concluidas': Feature.objects.filter(coluna__board=board, coluna__titulo='Concluído',
                                                      arquivado=False).count(),
        'membros_ativos': board.projeto.membros.count()
    }

    # Verificar gargalos WIP
    try:
        from apps.core.utils import verificar_gargalos_wip
        gargalos = verificar_gargalos_wip(board)
    except Exception as e:
        # Log do erro mas não quebra a página
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao verificar gargalos WIP: {e}")
        gargalos = []

    context = {
        'title': f'{board.titulo} - Kanban',
        'board': board,
        'colunas': colunas,
        'stats': stats,
        'gargalos': gargalos,
        'pode_editar': VortexPermissions.pode_editar_projeto(request.user, board.projeto),
        'websocket_group': f'board_{board_id}'  # Para conectar WebSocket
    }

    return render(request, 'board/kanban.html', context)

@login_required
@require_POST
@csrf_exempt  # Para HTMX/AJAX requests
def mover_item_ajax(request):
    """
    Move item entre colunas via AJAX/WebSocket
    Usado pelo drag-and-drop
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        item_type = data.get('item_type')  # 'bug' ou 'feature'
        nova_coluna_id = data.get('nova_coluna_id')
        nova_ordem = data.get('nova_ordem', 0)

        # Validar parâmetros
        if not all([item_id, item_type, nova_coluna_id]):
            return JsonResponse({'success': False, 'error': 'Parâmetros inválidos'})

        # Buscar item baseado no tipo
        if item_type == 'bug':
            item = get_object_or_404(Bug, id=item_id)
        elif item_type == 'feature':
            item = get_object_or_404(Feature, id=item_id)
        else:
            return JsonResponse({'success': False, 'error': 'Tipo de item inválido'})

        # Verificar permissão
        if not VortexPermissions.pode_mover_item(request.user, item):
            return JsonResponse({'success': False, 'error': 'Sem permissão para mover item'})

        # Buscar nova coluna
        nova_coluna = get_object_or_404(Coluna, id=nova_coluna_id)

        # Verificar se pode adicionar item (WIP limit)
        if not nova_coluna.pode_adicionar_item() and nova_coluna != item.coluna:
            return JsonResponse({
                'success': False,
                'error': f'Coluna {nova_coluna.titulo} atingiu limite WIP ({nova_coluna.limite_wip})'
            })

        # Atualizar item
        coluna_anterior = item.coluna
        item.coluna = nova_coluna
        item.ordem = nova_ordem
        item.save()

        # Enviar atualização via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'board_{nova_coluna.board.id}',
            {
                'type': 'item_moved',
                'message': {
                    'item_id': item_id,
                    'item_type': item_type,
                    'item_titulo': item.titulo,
                    'coluna_anterior': coluna_anterior.titulo,
                    'nova_coluna': nova_coluna.titulo,
                    'usuario': request.user.get_full_name() or request.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'{item.get_tipo_display()} movid{("o" if item_type == "bug" else "a")} para {nova_coluna.titulo}'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Adicionar estas views ao apps/core/views.py

@login_required
@require_http_methods(["GET", "POST"])
def criar_projeto_modal(request):
    """
    Modal para criar novo projeto
    """
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        cliente = request.POST.get('cliente', '').strip()
        descricao = request.POST.get('descricao', '').strip()

        # Validações
        if not nome:
            messages.error(request, 'Nome do projeto é obrigatório')
            return redirect('core:painel')

        if not cliente:
            messages.error(request, 'Cliente é obrigatório')
            return redirect('core:painel')

        # Verificar se já existe projeto com mesmo nome
        if Projeto.objects.filter(nome=nome).exists():
            messages.error(request, 'Já existe um projeto com este nome')
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

            # Criar board padrão
            board = Board.objects.create(
                titulo=f'{nome} - Sprint 1',
                projeto=projeto,
                descricao='Board principal do projeto'
            )

            messages.success(request, f'Projeto "{nome}" criado com sucesso!')
            return redirect('board:kanban', board_id=board.id)

        except Exception as e:
            messages.error(request, f'Erro ao criar projeto: {str(e)}')
            return redirect('core:painel')

    # GET - Exibir formulário
    context = {
        'usuarios': Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
    }

    return render(request, 'core/criar_projeto_modal.html', context)


@login_required
def notificacoes_usuario(request):
    """
    Lista notificações do usuário (sistema básico)
    """
    # Sistema básico de notificações usando mensagens Django
    notificacoes = []

    # Adicionar notificações baseadas em tarefas atrasadas
    tarefas_atrasadas = Bug.objects.filter(
        responsavel=request.user,
        prazo__lt=timezone.now().date(),
        arquivado=False
    ).exclude(coluna__titulo='Concluído')

    for tarefa in tarefas_atrasadas[:5]:  # Máximo 5
        notificacoes.append({
            'tipo': 'warning',
            'titulo': 'Tarefa Atrasada',
            'mensagem': f'Bug #{tarefa.id}: {tarefa.titulo}',
            'data': tarefa.prazo,
            'url': f'/board/item/bug/{tarefa.id}/',
            'icone': '⚠️'
        })

    # Notificações de features atrasadas
    features_atrasadas = Feature.objects.filter(
        responsavel=request.user,
        prazo__lt=timezone.now().date(),
        arquivado=False
    ).exclude(coluna__titulo='Concluído')

    for feature in features_atrasadas[:5]:
        notificacoes.append({
            'tipo': 'warning',
            'titulo': 'Feature Atrasada',
            'mensagem': f'Feature #{feature.id}: {feature.titulo}',
            'data': feature.prazo,
            'url': f'/board/item/feature/{feature.id}/',
            'icone': '⚠️'
        })

    # Notificações de novos projetos (se for admin/gerente)
    if request.user.tipo in ['admin', 'gerente']:
        projetos_recentes = Projeto.objects.filter(
            criado_em__gte=timezone.now() - timedelta(days=7)
        ).exclude(criado_por=request.user)[:3]

        for projeto in projetos_recentes:
            notificacoes.append({
                'tipo': 'info',
                'titulo': 'Novo Projeto',
                'mensagem': f'Projeto "{projeto.nome}" criado por {projeto.criado_por.get_full_name()}',
                'data': projeto.criado_em.date(),
                'url': f'/painel/',
                'icone': '📁'
            })

    # Ordenar por data (mais recentes primeiro)
    notificacoes.sort(key=lambda x: x['data'], reverse=True)

    context = {
        'notificacoes': notificacoes[:10],  # Máximo 10 notificações
        'total_nao_lidas': len([n for n in notificacoes if n['tipo'] == 'warning'])
    }

    return JsonResponse(context)


@login_required
@require_http_methods(["GET", "POST"])
def criar_item_modal(request, board_id):
    """
    Modal para criar novo item (Bug ou Feature)
    """
    board = get_object_or_404(Board, id=board_id)

    # Verificar acesso
    if not VortexPermissions.tem_acesso_board(request.user, board):
        messages.error(request, 'Sem acesso ao board')
        return redirect('painel')

    if request.method == 'POST':
        tipo_item = request.POST.get('tipo_item')
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao', '')
        coluna_id = request.POST.get('coluna_id')
        responsavel_id = request.POST.get('responsavel_id')
        prioridade = request.POST.get('prioridade', 'media')
        prazo = request.POST.get('prazo') or None

        # Validações básicas
        if not all([tipo_item, titulo, coluna_id]):
            messages.error(request, 'Preencha os campos obrigatórios')
            return redirect('board:kanban', board_id=board_id)

        try:
            coluna = board.colunas.get(id=coluna_id)
            responsavel = board.projeto.membros.get(id=responsavel_id) if responsavel_id else None

            # Criar item baseado no tipo
            if tipo_item == 'bug':
                severidade = request.POST.get('severidade', 'media')
                ambiente = request.POST.get('ambiente', 'produção')
                passos_reproducao = request.POST.get('passos_reproducao', '')

                item = Bug.objects.create(
                    titulo=titulo,
                    descricao=descricao,
                    coluna=coluna,
                    responsavel=responsavel,
                    prioridade=prioridade,
                    prazo=prazo,
                    severidade=severidade,
                    ambiente=ambiente,
                    passos_reproducao=passos_reproducao,
                    criado_por=request.user
                )

            elif tipo_item == 'feature':
                categoria = request.POST.get('categoria', 'backend')
                estimativa_horas = request.POST.get('estimativa_horas', 0)
                especificacao_url = request.POST.get('especificacao_url', '')

                item = Feature.objects.create(
                    titulo=titulo,
                    descricao=descricao,
                    coluna=coluna,
                    responsavel=responsavel,
                    prioridade=prioridade,
                    prazo=prazo,
                    categoria=categoria,
                    estimativa_horas=float(estimativa_horas) if estimativa_horas else 0,
                    especificacao_url=especificacao_url,
                    criado_por=request.user
                )

            # Notificar via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'board_{board_id}',
                {
                    'type': 'item_created',
                    'message': {
                        'item_id': item.id,
                        'item_type': tipo_item,
                        'item_titulo': item.titulo,
                        'coluna': coluna.titulo,
                        'usuario': request.user.get_full_name() or request.user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

            messages.success(request, f'{item.get_tipo_display()} criado com sucesso!')

        except Exception as e:
            messages.error(request, f'Erro ao criar item: {str(e)}')

        return redirect('board:kanban', board_id=board_id)

    # GET - Exibir formulário
    colunas = board.colunas.order_by('ordem')
    membros = board.projeto.membros.filter(is_active=True).order_by('first_name', 'username')

    context = {
        'board': board,
        'colunas': colunas,
        'membros': membros,
        'Bug': Bug,  # Para choices no template
        'Feature': Feature,
    }

    return render(request, 'board/criar_item_modal.html', context)


@login_required
def detalhes_item_modal(request, item_type, item_id):
    """
    Modal com detalhes completos do item
    Inclui comentários, registros de hora, histórico
    """
    # Buscar item baseado no tipo
    if item_type == 'bug':
        item = get_object_or_404(Bug.objects.select_related('coluna__board__projeto', 'responsavel', 'criado_por'),
                                 id=item_id)
    elif item_type == 'feature':
        item = get_object_or_404(Feature.objects.select_related('coluna__board__projeto', 'responsavel', 'criado_por'),
                                 id=item_id)
    else:
        messages.error(request, 'Tipo de item inválido')
        return redirect('painel')

    # Verificar acesso
    if not VortexPermissions.tem_acesso_board(request.user, item.coluna.board):
        messages.error(request, 'Sem acesso ao item')
        return redirect('painel')

    # Buscar comentários
    if item_type == 'bug':
        comentarios = item.comentarios.select_related('usuario').order_by('-criado_em')
        registros_hora = item.registros_hora.select_related('usuario').order_by('-inicio')
    else:
        comentarios = item.comentarios.select_related('usuario').order_by('-criado_em')
        registros_hora = item.registros_hora.select_related('usuario').order_by('-inicio')

    # Calcular total de horas
    total_horas = sum(r.duracao for r in registros_hora if r.duracao)

    context = {
        'item': item,
        'item_type': item_type,
        'comentarios': comentarios,
        'registros_hora': registros_hora,
        'total_horas': total_horas,
        'pode_editar': VortexPermissions.pode_editar_item(request.user, item),
        'pode_comentar': VortexPermissions.pode_comentar_item(request.user, item),
        'pode_registrar_hora': VortexPermissions.pode_registrar_hora(request.user, item),
    }

    return render(request, 'board/detalhes_item_modal.html', context)


@login_required
@require_POST
def adicionar_comentario(request, item_type, item_id):
    """
    Adiciona comentário a um item via HTMX
    """
    # Buscar item
    if item_type == 'bug':
        item = get_object_or_404(Bug, id=item_id)
    elif item_type == 'feature':
        item = get_object_or_404(Feature, id=item_id)
    else:
        return JsonResponse({'success': False, 'error': 'Tipo inválido'})

    # Verificar permissão
    if not VortexPermissions.pode_comentar_item(request.user, item):
        return JsonResponse({'success': False, 'error': 'Sem permissão'})

    texto = request.POST.get('texto', '').strip()
    if not texto:
        return JsonResponse({'success': False, 'error': 'Comentário não pode estar vazio'})

    # Criar comentário
    comentario_data = {
        'usuario': request.user,
        'texto': texto
    }

    if item_type == 'bug':
        comentario_data['bug'] = item
    else:
        comentario_data['feature'] = item

    comentario = Comentario.objects.create(**comentario_data)

    # Notificar via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'board_{item.coluna.board.id}',
        {
            'type': 'comment_added',
            'message': {
                'item_id': item_id,
                'item_type': item_type,
                'item_titulo': item.titulo,
                'comentario_texto': texto[:50] + '...' if len(texto) > 50 else texto,
                'usuario': request.user.get_full_name() or request.user.username,
                'timestamp': timezone.now().isoformat()
            }
        }
    )

    # Retornar HTML do comentário para HTMX
    context = {
        'comentario': comentario,
        'user': request.user
    }

    html = render(request, 'board/partials/comentario_item.html', context).content.decode()

    return JsonResponse({
        'success': True,
        'html': html,
        'message': 'Comentário adicionado'
    })


@login_required
@require_POST
def iniciar_registro_hora(request, item_type, item_id):
    """
    Inicia registro de horas em um item
    """
    # Buscar item
    if item_type == 'bug':
        item = get_object_or_404(Bug, id=item_id)
    elif item_type == 'feature':
        item = get_object_or_404(Feature, id=item_id)
    else:
        return JsonResponse({'success': False, 'error': 'Tipo inválido'})

    # Verificar permissão
    if not VortexPermissions.pode_registrar_hora(request.user, item):
        return JsonResponse({'success': False, 'error': 'Apenas o responsável pode registrar horas'})

    # Verificar se já existe registro em aberto
    registro_ativo = RegistroHora.objects.filter(
        usuario=request.user,
        fim__isnull=True
    ).first()

    if registro_ativo:
        return JsonResponse({
            'success': False,
            'error': f'Finalize primeiro o registro em "{registro_ativo.item}"'
        })

    # Criar novo registro
    registro_data = {
        'usuario': request.user,
        'inicio': timezone.now(),
        'descricao': request.POST.get('descricao', f'Trabalhando em {item.titulo}')
    }

    if item_type == 'bug':
        registro_data['bug'] = item
    else:
        registro_data['feature'] = item

    registro = RegistroHora.objects.create(**registro_data)

    return JsonResponse({
        'success': True,
        'registro_id': registro.id,
        'message': 'Registro de hora iniciado'
    })


@login_required
@require_POST
def finalizar_registro_hora(request, registro_id):
    """
    Finaliza registro de horas
    """
    registro = get_object_or_404(RegistroHora, id=registro_id, usuario=request.user, fim__isnull=True)

    registro.fim = timezone.now()
    registro.save()

    return JsonResponse({
        'success': True,
        'duracao': registro.duracao,
        'message': f'Registro finalizado: {registro.duracao:.1f}h'
    })


@login_required
def buscar_items(request, board_id):
    """
    Busca items no board (para filtros e pesquisa)
    """
    board = get_object_or_404(Board, id=board_id)

    # Verificar acesso
    if not VortexPermissions.tem_acesso_board(request.user, board):
        return JsonResponse({'error': 'Sem acesso'}, status=403)

    query = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', 'todos')  # 'bug', 'feature', 'todos'
    responsavel = request.GET.get('responsavel')
    prioridade = request.GET.get('prioridade')

    # Base QuerySets
    bugs = Bug.objects.filter(coluna__board=board, arquivado=False)
    features = Feature.objects.filter(coluna__board=board, arquivado=False)

    # Aplicar filtros
    if query:
        bugs = bugs.filter(Q(titulo__icontains=query) | Q(descricao__icontains=query))
        features = features.filter(Q(titulo__icontains=query) | Q(descricao__icontains=query))

    if responsavel:
        bugs = bugs.filter(responsavel__id=responsavel)
        features = features.filter(responsavel__id=responsavel)

    if prioridade:
        bugs = bugs.filter(prioridade=prioridade)
        features = features.filter(prioridade=prioridade)

    # Montar resultados
    resultados = []

    if tipo in ['bug', 'todos']:
        for bug in bugs.select_related('responsavel', 'coluna')[:20]:
            resultados.append({
                'id': bug.id,
                'tipo': 'bug',
                'titulo': bug.titulo,
                'responsavel': bug.responsavel.get_full_name() if bug.responsavel else None,
                'coluna': bug.coluna.titulo,
                'prioridade': bug.get_prioridade_display(),
                'severidade': bug.get_severidade_display(),
            })

    if tipo in ['feature', 'todos']:
        for feature in features.select_related('responsavel', 'coluna')[:20]:
            resultados.append({
                'id': feature.id,
                'tipo': 'feature',
                'titulo': feature.titulo,
                'responsavel': feature.responsavel.get_full_name() if feature.responsavel else None,
                'coluna': feature.coluna.titulo,
                'prioridade': feature.get_prioridade_display(),
                'categoria': feature.get_categoria_display(),
            })

    return JsonResponse({
        'resultados': resultados,
        'total': len(resultados)
    })


@login_required
def board_metricas(request, board_id):
    """
    Página de métricas e analytics do board
    """
    board = get_object_or_404(Board, id=board_id)

    # Verificar acesso
    if not VortexPermissions.tem_acesso_board(request.user, board):
        messages.error(request, 'Sem acesso ao board')
        return redirect('painel')

    # Importar funções de métricas
    from apps.core.utils import (
        calcular_velocidade_equipe,
        gerar_burndown_chart_data,
        calcular_distribuicao_tarefas
    )

    # Calcular métricas
    velocidade = calcular_velocidade_equipe(board.projeto)
    burndown = gerar_burndown_chart_data(board)
    distribuicao = calcular_distribuicao_tarefas(board.projeto)

    context = {
        'title': f'Métricas - {board.titulo}',
        'board': board,
        'velocidade': velocidade,
        'burndown': burndown,
        'distribuicao': distribuicao,
    }

    return render(request, 'board/metricas.html', context)