# apps/relatorios/views.py

import csv
import json
from django.db.models import Sum, F, ExpressionWrapper, fields
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.contrib import messages

# Imports para PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

# Imports para Excel
import xlsxwriter
from io import BytesIO

from apps.core.models import Projeto, Board, Bug, Feature, Usuario, RegistroHora
from apps.core.permissions import requer_acesso_projeto, VortexPermissions
from .utils import (
    gerar_dados_burndown_avancado,
    calcular_metricas_produtividade,
    gerar_grafico_velocidade,
    calcular_distribuicao_trabalho
)


@login_required
def dashboard_relatorios(request):
    """
    Dashboard principal dos relatórios
    Lista relatórios disponíveis e permite filtros
    """
    # Verificar se usuário pode acessar relatórios
    if not VortexPermissions.is_gerente_ou_admin(request.user):
        messages.error(request, 'Acesso restrito a gerentes e administradores.')
        return redirect('painel')

    # Projetos que o usuário tem acesso
    if request.user.tipo == 'admin':
        projetos = Projeto.objects.filter(ativo=True)
    else:
        projetos = Projeto.objects.filter(
            membros=request.user,
            ativo=True
        )

    # Estatísticas gerais
    stats = {
        'total_projetos': projetos.count(),
        'total_bugs': Bug.objects.filter(coluna__board__projeto__in=projetos).count(),
        'total_features': Feature.objects.filter(coluna__board__projeto__in=projetos).count(),
        'bugs_concluidos': Bug.objects.filter(
            coluna__board__projeto__in=projetos,
            coluna__titulo='Concluído'
        ).count(),
        'features_concluidas': Feature.objects.filter(
            coluna__board__projeto__in=projetos,
            coluna__titulo='Concluído'
        ).count(),
    }

    # Horas trabalhadas no último mês
    ultimo_mes = timezone.now() - timedelta(days=30)

    # Query base para registros de hora
    registros_horas_qs = RegistroHora.objects.filter(
        Q(bug__coluna__board__projeto__in=projetos) |
        Q(feature__coluna__board__projeto__in=projetos),
        inicio__gte=ultimo_mes,
        fim__isnull=False  # Garante que 'fim' não seja nulo para o cálculo
    )

    # Calcular a soma das durações no banco de dados
    aggregated_data = registros_horas_qs.aggregate(
        total_duration=Sum(ExpressionWrapper(F('fim') - F('inicio'), output_field=fields.DurationField()))
    )

    total_duration_timedelta = aggregated_data['total_duration']

    if total_duration_timedelta:
        # Converter o timedelta total para horas
        stats['horas_ultimo_mes'] = round(total_duration_timedelta.total_seconds() / 3600, 2)
    else:
        stats['horas_ultimo_mes'] = 0

    context = {
        'title': 'Relatórios - Dashboard',
        'projetos': projetos,
        'stats': stats,
    }

    return render(request, 'relatorios/dashboard.html', context)


@login_required
@requer_acesso_projeto
def relatorio_projeto_pdf(request, projeto_id):
    """
    Gera relatório completo do projeto em PDF
    """
    projeto = request.projeto  # Injetado pelo decorator

    # Criar response HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{projeto.nome.replace(" ", "_")}.pdf"'

    # Criar documento PDF
    doc = SimpleDocTemplate(response, pagesize=A4)
    story = []

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        textColor=colors.darkblue
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )

    # Título do relatório
    story.append(Paragraph(f"Relatório do Projeto: {projeto.nome}", title_style))
    story.append(Paragraph(f"Cliente: {projeto.cliente}", styles['Normal']))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Informações gerais
    story.append(Paragraph("📋 Informações Gerais", heading_style))

    info_data = [
        ['Campo', 'Valor'],
        ['Projeto', projeto.nome],
        ['Cliente', projeto.cliente],
        ['Criado por', projeto.criado_por.get_full_name() or projeto.criado_por.username],
        ['Data de criação', projeto.criado_em.strftime('%d/%m/%Y')],
        ['Membros da equipe', str(projeto.membros.count())],
        ['Status', 'Ativo' if projeto.ativo else 'Inativo'],
    ]

    info_table = Table(info_data)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(info_table)
    story.append(Spacer(1, 20))

    # Estatísticas de bugs e features
    story.append(Paragraph("🐛 Estatísticas de Bugs", heading_style))

    bugs = Bug.objects.filter(coluna__board__projeto=projeto)
    bugs_stats = [
        ['Métrica', 'Valor'],
        ['Total de Bugs', str(bugs.count())],
        ['Bugs Concluídos', str(bugs.filter(coluna__titulo='Concluído').count())],
        ['Bugs Críticos', str(bugs.filter(severidade='critica').count())],
        ['Bugs em Progresso', str(bugs.filter(coluna__titulo='Em Progresso').count())],
    ]

    bugs_table = Table(bugs_stats)
    bugs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(bugs_table)
    story.append(Spacer(1, 20))

    # Estatísticas de features
    story.append(Paragraph("✨ Estatísticas de Features", heading_style))

    features = Feature.objects.filter(coluna__board__projeto=projeto)
    features_stats = [
        ['Métrica', 'Valor'],
        ['Total de Features', str(features.count())],
        ['Features Concluídas', str(features.filter(coluna__titulo='Concluído').count())],
        ['Horas Estimadas Total', f"{features.aggregate(total=Sum('estimativa_horas'))['total'] or 0}h"],
        ['Features em Progresso', str(features.filter(coluna__titulo='Em Progresso').count())],
    ]

    features_table = Table(features_stats)
    features_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(features_table)
    story.append(Spacer(1, 20))

    # Lista de membros da equipe
    story.append(Paragraph("👥 Equipe do Projeto", heading_style))

    membros_data = [['Nome', 'Email', 'Tipo', 'Tarefas Ativas']]

    for membro in projeto.membros.all():
        tarefas_ativas = (
                bugs.filter(responsavel=membro).exclude(coluna__titulo='Concluído').count() +
                features.filter(responsavel=membro).exclude(coluna__titulo='Concluído').count()
        )

        membros_data.append([
            membro.get_full_name() or membro.username,
            membro.email,
            membro.get_tipo_display(),
            str(tarefas_ativas)
        ])

    membros_table = Table(membros_data)
    membros_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(membros_table)
    story.append(Spacer(1, 20))

    # Boards do projeto
    story.append(Paragraph("📋 Boards do Projeto", heading_style))

    boards = projeto.boards.all()
    if boards:
        boards_data = [['Board', 'Bugs', 'Features', 'Status']]

        for board in boards:
            board_bugs = bugs.filter(coluna__board=board).count()
            board_features = features.filter(coluna__board=board).count()

            boards_data.append([
                board.titulo,
                str(board_bugs),
                str(board_features),
                'Ativo' if board.ativo else 'Inativo'
            ])

        boards_table = Table(boards_data)
        boards_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(boards_table)
    else:
        story.append(Paragraph("Nenhum board encontrado neste projeto.", styles['Normal']))

    # Rodapé
    story.append(Spacer(1, 30))
    story.append(Paragraph("—" * 50, styles['Normal']))
    story.append(Paragraph("Relatório gerado pelo Vortex Board", styles['Normal']))
    story.append(Paragraph(f"Vórtex Startup © {datetime.now().year}", styles['Normal']))

    # Construir PDF
    doc.build(story)
    return response


@login_required
@requer_acesso_projeto
def exportar_projeto_csv(request, projeto_id):
    """
    Exporta dados do projeto para CSV
    """
    projeto = request.projeto

    # Criar response HTTP para CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="projeto_{projeto.nome.replace(" ", "_")}.csv"'
    response.write('\ufeff')  # BOM para UTF-8

    writer = csv.writer(response)

    # Cabeçalho
    writer.writerow([
        'Tipo', 'ID', 'Título', 'Descrição', 'Responsável',
        'Prioridade', 'Status', 'Coluna', 'Board', 'Criado em',
        'Prazo', 'Pontos', 'Severidade/Categoria', 'Ambiente/Horas Est.'
    ])

    # Bugs
    bugs = Bug.objects.filter(
        coluna__board__projeto=projeto
    ).select_related('responsavel', 'coluna', 'coluna__board')

    for bug in bugs:
        writer.writerow([
            'Bug',
            bug.id,
            bug.titulo,
            bug.descricao,
            bug.responsavel.get_full_name() if bug.responsavel else '',
            bug.get_prioridade_display(),
            'Concluído' if bug.coluna.titulo == 'Concluído' else 'Em Andamento',
            bug.coluna.titulo,
            bug.coluna.board.titulo,
            bug.criado_em.strftime('%d/%m/%Y'),
            bug.prazo.strftime('%d/%m/%Y') if bug.prazo else '',
            bug.calcular_pontos(),
            bug.get_severidade_display(),
            bug.ambiente
        ])

    # Features
    features = Feature.objects.filter(
        coluna__board__projeto=projeto
    ).select_related('responsavel', 'coluna', 'coluna__board')

    for feature in features:
        writer.writerow([
            'Feature',
            feature.id,
            feature.titulo,
            feature.descricao,
            feature.responsavel.get_full_name() if feature.responsavel else '',
            feature.get_prioridade_display(),
            'Concluída' if feature.coluna.titulo == 'Concluído' else 'Em Andamento',
            feature.coluna.titulo,
            feature.coluna.board.titulo,
            feature.criado_em.strftime('%d/%m/%Y'),
            feature.prazo.strftime('%d/%m/%Y') if feature.prazo else '',
            feature.calcular_pontos(),
            feature.get_categoria_display(),
            f"{feature.estimativa_horas}h"
        ])

    return response


@login_required
@requer_acesso_projeto
def exportar_projeto_excel(request, projeto_id):
    """
    Exporta dados do projeto para Excel (XLSX)
    Com múltiplas abas e formatação avançada
    """
    projeto = request.projeto

    # Criar arquivo Excel em memória
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Formatos
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'border': 1
    })

    cell_format = workbook.add_format({'border': 1})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
    number_format = workbook.add_format({'num_format': '0.00', 'border': 1})

    # Aba 1: Resumo do Projeto
    resumo_sheet = workbook.add_worksheet('Resumo')
    resumo_sheet.write('A1', 'RELATÓRIO DO PROJETO', header_format)
    resumo_sheet.write('A3', 'Nome:', header_format)
    resumo_sheet.write('B3', projeto.nome, cell_format)
    resumo_sheet.write('A4', 'Cliente:', header_format)
    resumo_sheet.write('B4', projeto.cliente, cell_format)
    resumo_sheet.write('A5', 'Criado em:', header_format)
    resumo_sheet.write('B5', projeto.criado_em, date_format)
    resumo_sheet.write('A6', 'Membros:', header_format)
    resumo_sheet.write('B6', projeto.membros.count(), cell_format)

    # Estatísticas
    bugs_total = Bug.objects.filter(coluna__board__projeto=projeto).count()
    features_total = Feature.objects.filter(coluna__board__projeto=projeto).count()
    bugs_concluidos = Bug.objects.filter(coluna__board__projeto=projeto, coluna__titulo='Concluído').count()
    features_concluidas = Feature.objects.filter(coluna__board__projeto=projeto, coluna__titulo='Concluído').count()

    resumo_sheet.write('A8', 'ESTATÍSTICAS', header_format)
    resumo_sheet.write('A9', 'Total de Bugs:', header_format)
    resumo_sheet.write('B9', bugs_total, cell_format)
    resumo_sheet.write('A10', 'Bugs Concluídos:', header_format)
    resumo_sheet.write('B10', bugs_concluidos, cell_format)
    resumo_sheet.write('A11', 'Total de Features:', header_format)
    resumo_sheet.write('B11', features_total, cell_format)
    resumo_sheet.write('A12', 'Features Concluídas:', header_format)
    resumo_sheet.write('B12', features_concluidas, cell_format)

    # Aba 2: Bugs
    bugs_sheet = workbook.add_worksheet('Bugs')
    bug_headers = [
        'ID', 'Título', 'Descrição', 'Responsável', 'Prioridade',
        'Severidade', 'Ambiente', 'Coluna', 'Board', 'Criado em',
        'Prazo', 'Pontos', 'Status'
    ]

    for col, header in enumerate(bug_headers):
        bugs_sheet.write(0, col, header, header_format)

    bugs = Bug.objects.filter(
        coluna__board__projeto=projeto
    ).select_related('responsavel', 'coluna', 'coluna__board')

    for row, bug in enumerate(bugs, 1):
        bugs_sheet.write(row, 0, bug.id, cell_format)
        bugs_sheet.write(row, 1, bug.titulo, cell_format)
        bugs_sheet.write(row, 2, bug.descricao, cell_format)
        bugs_sheet.write(row, 3, bug.responsavel.get_full_name() if bug.responsavel else '', cell_format)
        bugs_sheet.write(row, 4, bug.get_prioridade_display(), cell_format)
        bugs_sheet.write(row, 5, bug.get_severidade_display(), cell_format)
        bugs_sheet.write(row, 6, bug.ambiente, cell_format)
        bugs_sheet.write(row, 7, bug.coluna.titulo, cell_format)
        bugs_sheet.write(row, 8, bug.coluna.board.titulo, cell_format)
        bugs_sheet.write(row, 9, bug.criado_em, date_format)
        bugs_sheet.write(row, 10, bug.prazo if bug.prazo else '', date_format)
        bugs_sheet.write(row, 11, bug.calcular_pontos(), cell_format)
        bugs_sheet.write(row, 12, 'Concluído' if bug.coluna.titulo == 'Concluído' else 'Em Andamento', cell_format)

    # Aba 3: Features
    features_sheet = workbook.add_worksheet('Features')
    feature_headers = [
        'ID', 'Título', 'Descrição', 'Responsável', 'Prioridade',
        'Categoria', 'Horas Estimadas', 'Coluna', 'Board', 'Criado em',
        'Prazo', 'Pontos', 'Status'
    ]

    for col, header in enumerate(feature_headers):
        features_sheet.write(0, col, header, header_format)

    features = Feature.objects.filter(
        coluna__board__projeto=projeto
    ).select_related('responsavel', 'coluna', 'coluna__board')

    for row, feature in enumerate(features, 1):
        features_sheet.write(row, 0, feature.id, cell_format)
        features_sheet.write(row, 1, feature.titulo, cell_format)
        features_sheet.write(row, 2, feature.descricao, cell_format)
        features_sheet.write(row, 3, feature.responsavel.get_full_name() if feature.responsavel else '', cell_format)
        features_sheet.write(row, 4, feature.get_prioridade_display(), cell_format)
        features_sheet.write(row, 5, feature.get_categoria_display(), cell_format)
        features_sheet.write(row, 6, float(feature.estimativa_horas), number_format)
        features_sheet.write(row, 7, feature.coluna.titulo, cell_format)
        features_sheet.write(row, 8, feature.coluna.board.titulo, cell_format)
        features_sheet.write(row, 9, feature.criado_em, date_format)
        features_sheet.write(row, 10, feature.prazo if feature.prazo else '', date_format)
        features_sheet.write(row, 11, feature.calcular_pontos(), cell_format)
        features_sheet.write(row, 12, 'Concluída' if feature.coluna.titulo == 'Concluído' else 'Em Andamento',
                             cell_format)

    # Ajustar largura das colunas
    for sheet in [resumo_sheet, bugs_sheet, features_sheet]:
        sheet.set_column('A:M', 15)

    # Fechar workbook e preparar response
    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="projeto_{projeto.nome.replace(" ", "_")}.xlsx"'

    return response


@login_required
def relatorio_horas_usuario(request):
    """
    Relatório de horas trabalhadas por usuário
    """
    if not VortexPermissions.is_gerente_ou_admin(request.user):
        messages.error(request, 'Acesso restrito.')
        return redirect('painel')

    # Filtros
    usuario_id = request.GET.get('usuario')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Query base
    registros = RegistroHora.objects.filter(fim__isnull=False)

    # Aplicar filtros
    if usuario_id:
        registros = registros.filter(usuario_id=usuario_id)

    if data_inicio:
        registros = registros.filter(inicio__date__gte=data_inicio)

    if data_fim:
        registros = registros.filter(inicio__date__lte=data_fim)

    # Se for CSV
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_horas.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            'Usuário', 'Item', 'Tipo', 'Descrição',
            'Início', 'Fim', 'Duração (h)', 'Projeto'
        ])

        for registro in registros.select_related('usuario', 'bug', 'feature'):
            item = registro.bug or registro.feature
            writer.writerow([
                registro.usuario.get_full_name() or registro.usuario.username,
                item.titulo if item else '',
                'Bug' if registro.bug else 'Feature',
                registro.descricao,
                registro.inicio.strftime('%d/%m/%Y %H:%M'),
                registro.fim.strftime('%d/%m/%Y %H:%M'),
                f"{registro.duracao:.2f}",
                item.coluna.board.projeto.nome if item else ''
            ])

        return response

    # Página HTML
    usuarios = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')

    # Agrupar por usuário
    resumo_usuarios = {}
    for registro in registros.select_related('usuario'):
        user_id = registro.usuario.id
        if user_id not in resumo_usuarios:
            resumo_usuarios[user_id] = {
                'usuario': registro.usuario,
                'total_horas': 0,
                'total_registros': 0
            }

        resumo_usuarios[user_id]['total_horas'] += registro.duracao
        resumo_usuarios[user_id]['total_registros'] += 1

    context = {
        'title': 'Relatório de Horas',
        'usuarios': usuarios,
        'registros': registros.select_related('usuario', 'bug', 'feature').order_by('-inicio')[:100],
        'resumo_usuarios': list(resumo_usuarios.values()),
        'filtros': {
            'usuario_id': usuario_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }
    }

    return render(request, 'relatorios/horas_usuario.html', context)


@login_required
def api_metricas_dashboard(request):
    """
    API JSON para dashboard de métricas
    Usado para gráficos dinâmicos
    """
    if not VortexPermissions.is_gerente_ou_admin(request.user):
        return JsonResponse({'error': 'Sem permissão'}, status=403)

    # Projetos acessíveis
    if request.user.tipo == 'admin':
        projetos = Projeto.objects.filter(ativo=True)
    else:
        projetos = Projeto.objects.filter(membros=request.user, ativo=True)

    # Dados dos últimos 30 dias
    dias_passados = 30
    fim = timezone.now().date()
    inicio = fim - timedelta(days=dias_passados)

    # Bugs criados por dia
    bugs_por_dia = []
    features_por_dia = []

    for i in range(dias_passados):
        data = inicio + timedelta(days=i)

        bugs_count = Bug.objects.filter(
            coluna__board__projeto__in=projetos,
            criado_em__date=data
        ).count()

        features_count = Feature.objects.filter(
            coluna__board__projeto__in=projetos,
            criado_em__date=data
        ).count()

        bugs_por_dia.append({
            'data': data.strftime('%d/%m'),
            'count': bugs_count
        })

        features_por_dia.append({
            'data': data.strftime('%d/%m'),
            'count': features_count
        })

    # Distribuição por prioridade
    prioridades = ['baixa', 'media', 'alta', 'critica']
    distribuicao_prioridade = []

    for prioridade in prioridades:
        count = (
                Bug.objects.filter(coluna__board__projeto__in=projetos, prioridade=prioridade).count() +
                Feature.objects.filter(coluna__board__projeto__in=projetos, prioridade=prioridade).count()
        )

        distribuicao_prioridade.append({
            'prioridade': prioridade.title(),
            'count': count
        })

    # Top 5 usuários mais ativos
    usuarios_ativos = []
    for usuario in Usuario.objects.filter(is_active=True)[:10]:
        total_items = (
                Bug.objects.filter(responsavel=usuario, coluna__board__projeto__in=projetos).count() +
                Feature.objects.filter(responsavel=usuario, coluna__board__projeto__in=projetos).count()
        )

        if total_items > 0:
            usuarios_ativos.append({
                'nome': usuario.get_full_name() or usuario.username,
                'total_items': total_items
            })

    usuarios_ativos.sort(key=lambda x: x['total_items'], reverse=True)
    usuarios_ativos = usuarios_ativos[:5]

    return JsonResponse({
        'bugs_por_dia': bugs_por_dia,
        'features_por_dia': features_por_dia,
        'distribuicao_prioridade': distribuicao_prioridade,
        'usuarios_ativos': usuarios_ativos,
        'periodo': f"{inicio.strftime('%d/%m/%Y')} - {fim.strftime('%d/%m/%Y')}"
    })