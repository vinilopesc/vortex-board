# apps/core/management/commands/seed.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from apps.core.models import (
    Usuario, Projeto, Board, Coluna, Bug, Feature,
    RegistroHora, Comentario
)


class Command(BaseCommand):
    help = 'Popula o banco com dados iniciais para desenvolvimento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpa dados existentes antes de popular'
        )

    def handle(self, *args, **options):
        """Executa o seed do banco de dados"""

        if options['clear']:
            self.stdout.write('🗑️  Limpando dados existentes...')
            self._limpar_dados()

        self.stdout.write('🌱 Iniciando seed do banco de dados...')

        with transaction.atomic():
            usuarios = self._criar_usuarios()
            projeto = self._criar_projeto_demo(usuarios)
            board = self._criar_board_com_colunas(projeto)
            items = self._criar_items_demo(board, usuarios)
            self._criar_registros_hora(items, usuarios)
            self._criar_comentarios(items, usuarios)

        self.stdout.write(
            self.style.SUCCESS('✅ Seed concluído com sucesso!')
        )
        self._exibir_resumo()

    def _limpar_dados(self):
        """Remove todos os dados exceto superusuário original"""
        Comentario.objects.all().delete()
        RegistroHora.objects.all().delete()
        Bug.objects.all().delete()
        Feature.objects.all().delete()
        Coluna.objects.all().delete()
        Board.objects.all().delete()
        Projeto.objects.all().delete()

        # Manter apenas superusuários originais (criados fora do seed)
        usuarios_removidos = Usuario.objects.exclude(is_superuser=True).count()
        Usuario.objects.exclude(is_superuser=True).delete()

        if usuarios_removidos > 0:
            self.stdout.write(f'  🗑️  {usuarios_removidos} usuários removidos (superusuários mantidos)')
        else:
            self.stdout.write('  🗑️  Dados limpos')

    def _criar_usuarios(self):
        """Cria usuários com diferentes níveis de acesso (ou busca se já existem)"""
        self.stdout.write('👥 Criando/verificando usuários...')

        usuarios = {}
        usuarios_criados = 0
        usuarios_existentes = 0

        # Configurações dos usuários
        usuarios_config = [
            {
                'key': 'admin',
                'username': 'admin',
                'email': 'admin@vortex.com.br',
                'password': 'admin123',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'tipo': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'telefone': ''
            },
            {
                'key': 'vini',
                'username': 'vini',
                'email': 'vini@vortex.com.br',
                'password': 'vini123',
                'first_name': 'Vinícius',
                'last_name': 'Oliveira',
                'tipo': 'gerente',
                'is_staff': False,
                'is_superuser': False,
                'telefone': '(31) 98765-4321'
            },
            {
                'key': 'meira',
                'username': 'meira',
                'email': 'meira@vortex.com.br',
                'password': 'meira123',
                'first_name': 'João',
                'last_name': 'Meira',
                'tipo': 'gerente',
                'is_staff': False,
                'is_superuser': False,
                'telefone': '(31) 98765-4322'
            },
            {
                'key': 'alice',
                'username': 'alice',
                'email': 'alice@vortex.com.br',
                'password': 'alice123',
                'first_name': 'Alice',
                'last_name': 'Santos',
                'tipo': 'funcionario',
                'is_staff': False,
                'is_superuser': False,
                'telefone': '(31) 98765-4323'
            },
            {
                'key': 'bob',
                'username': 'bob',
                'email': 'bob@vortex.com.br',
                'password': 'bob123',
                'first_name': 'Roberto',
                'last_name': 'Silva',
                'tipo': 'funcionario',
                'is_staff': False,
                'is_superuser': False,
                'telefone': '(31) 98765-4324'
            },
            {
                'key': 'carol',
                'username': 'carol',
                'email': 'carol@vortex.com.br',
                'password': 'carol123',
                'first_name': 'Carolina',
                'last_name': 'Ferreira',
                'tipo': 'funcionario',
                'is_staff': False,
                'is_superuser': False,
                'telefone': '(31) 98765-4325'
            }
        ]

        # Criar ou buscar cada usuário
        for config in usuarios_config:
            try:
                # Tentar buscar usuário existente
                usuario = Usuario.objects.get(username=config['username'])
                usuarios[config['key']] = usuario
                usuarios_existentes += 1

            except Usuario.DoesNotExist:
                # Criar novo usuário se não existe
                usuario = Usuario.objects.create_user(
                    username=config['username'],
                    email=config['email'],
                    password=config['password'],
                    first_name=config['first_name'],
                    last_name=config['last_name'],
                    tipo=config['tipo'],
                    is_staff=config['is_staff'],
                    is_superuser=config['is_superuser'],
                    telefone=config['telefone']
                )
                usuarios[config['key']] = usuario
                usuarios_criados += 1

        self.stdout.write(f'  ✓ {usuarios_criados} usuários criados, {usuarios_existentes} já existiam')
        return usuarios

    def _criar_projeto_demo(self, usuarios):
        """Cria projeto de demonstração (ou busca se já existe)"""
        self.stdout.write('📁 Criando/verificando projeto demo...')

        projeto_nome = 'Demo Vortex'

        try:
            # Tentar buscar projeto existente
            projeto = Projeto.objects.get(nome=projeto_nome)
            self.stdout.write('  ✓ Projeto demo já existe')

        except Projeto.DoesNotExist:
            # Criar novo projeto se não existe
            projeto = Projeto.objects.create(
                nome=projeto_nome,
                cliente='Cliente Exemplo S.A.',
                descricao=(
                    'Projeto de demonstração do sistema Vortex Board. '
                    'Este projeto contém exemplos de todas as funcionalidades '
                    'disponíveis no sistema.'
                ),
                criado_por=usuarios['vini']
            )
            self.stdout.write('  ✓ Projeto demo criado')

        # Garantir que todos os usuários são membros
        projeto.membros.set(usuarios.values())

        return projeto

    def _criar_board_com_colunas(self, projeto):
        """Cria board com colunas customizadas (ou busca se já existe)"""
        self.stdout.write('📋 Criando/verificando board e colunas...')

        board_titulo = 'Sprint 1 - MVP'

        try:
            # Tentar buscar board existente
            board = Board.objects.get(titulo=board_titulo, projeto=projeto)
            self.stdout.write('  ✓ Board já existe')

        except Board.DoesNotExist:
            # Criar novo board se não existe
            board = Board.objects.create(
                titulo=board_titulo,
                projeto=projeto,
                descricao='Primeira sprint do projeto Demo Vortex'
            )
            self.stdout.write('  ✓ Board criado')

        # Aguardar signal criar colunas padrão, depois customizar
        # O signal post_save já criou colunas básicas

        # Configurações customizadas para as colunas
        colunas_config = {
            'Backlog': {'cor': '#6B7280', 'limite_wip': 0},  # Cinza
            'Em Progresso': {'cor': '#3B82F6', 'limite_wip': 3},  # Azul
            'Em Revisão': {'cor': '#F59E0B', 'limite_wip': 2},  # Amarelo
            'Concluído': {'cor': '#10B981', 'limite_wip': 0},  # Verde
        }

        # Atualizar colunas criadas pelo signal com configurações específicas
        colunas_atualizadas = 0
        for coluna in board.colunas.all():
            if coluna.titulo in colunas_config:
                config = colunas_config[coluna.titulo]
                # Só atualizar se necessário
                if coluna.cor != config['cor'] or coluna.limite_wip != config['limite_wip']:
                    coluna.cor = config['cor']
                    coluna.limite_wip = config['limite_wip']
                    coluna.save()
                    colunas_atualizadas += 1

        if colunas_atualizadas > 0:
            self.stdout.write(f'  ✓ {colunas_atualizadas} colunas customizadas')
        else:
            self.stdout.write('  ✓ Colunas já customizadas')

        return board

    def _criar_items_demo(self, board, usuarios):
        """Cria bugs e features de demonstração (se não existirem)"""
        self.stdout.write('🎯 Criando/verificando items (bugs e features)...')

        # Verificar se já existem items neste board
        if Bug.objects.filter(coluna__board=board).exists() or Feature.objects.filter(coluna__board=board).exists():
            total_bugs = Bug.objects.filter(coluna__board=board).count()
            total_features = Feature.objects.filter(coluna__board=board).count()
            self.stdout.write(f'  ✓ Items já existem: {total_features} features, {total_bugs} bugs')
            # Retornar items existentes
            return list(Bug.objects.filter(coluna__board=board)) + list(Feature.objects.filter(coluna__board=board))

        colunas = board.colunas.all()
        items = []

        # Features
        features_data = [
            {
                'titulo': 'Implementar autenticação JWT',
                'descricao': 'Adicionar autenticação via tokens JWT para a API REST',
                'categoria': 'backend',
                'prioridade': 'alta',
                'estimativa_horas': 16,
                'responsavel': usuarios['bob'],
                'coluna': colunas[1],  # Em Progresso
                'prazo': timezone.now().date() + timedelta(days=5)
            },
            {
                'titulo': 'Dashboard com gráficos',
                'descricao': 'Criar dashboard com Chart.js mostrando métricas do projeto',
                'categoria': 'frontend',
                'prioridade': 'media',
                'estimativa_horas': 12,
                'responsavel': usuarios['alice'],
                'coluna': colunas[1],  # Em Progresso
                'prazo': timezone.now().date() + timedelta(days=7)
            },
            {
                'titulo': 'Notificações em tempo real',
                'descricao': 'Sistema de notificações usando WebSockets',
                'categoria': 'backend',
                'prioridade': 'media',
                'estimativa_horas': 20,
                'responsavel': usuarios['carol'],
                'coluna': colunas[0],  # Backlog
                'prazo': timezone.now().date() + timedelta(days=14)
            },
            {
                'titulo': 'Refatorar componentes UI',
                'descricao': 'Melhorar componentes usando Tailwind CSS',
                'categoria': 'ux',
                'prioridade': 'baixa',
                'estimativa_horas': 8,
                'responsavel': usuarios['alice'],
                'coluna': colunas[2],  # Em Revisão
                'prazo': timezone.now().date() + timedelta(days=3)
            },
            {
                'titulo': 'Documentação da API',
                'descricao': 'Criar documentação completa usando Swagger/OpenAPI',
                'categoria': 'docs',
                'prioridade': 'alta',
                'estimativa_horas': 6,
                'responsavel': usuarios['bob'],
                'coluna': colunas[3],  # Concluído
                'prazo': timezone.now().date() - timedelta(days=2)
            }
        ]

        for idx, data in enumerate(features_data):
            feature = Feature.objects.create(
                titulo=data['titulo'],
                descricao=data['descricao'],
                categoria=data['categoria'],
                prioridade=data['prioridade'],
                estimativa_horas=data['estimativa_horas'],
                responsavel=data['responsavel'],
                coluna=data['coluna'],
                criado_por=usuarios['vini'],
                ordem=idx,
                prazo=data['prazo']
            )
            items.append(feature)

        # Bugs
        bugs_data = [
            {
                'titulo': 'Erro ao fazer login com email',
                'descricao': 'Sistema não aceita login usando email, apenas username',
                'severidade': 'alta',
                'ambiente': 'produção',
                'prioridade': 'alta',
                'responsavel': usuarios['bob'],
                'coluna': colunas[1],  # Em Progresso
                'passos_reproducao': (
                    '1. Acessar tela de login\n'
                    '2. Inserir email ao invés de username\n'
                    '3. Tentar fazer login\n'
                    '4. Sistema retorna erro 500'
                ),
                'prazo': timezone.now().date() + timedelta(days=1)
            },
            {
                'titulo': 'Layout quebrado no mobile',
                'descricao': 'Menu lateral não fecha corretamente em dispositivos móveis',
                'severidade': 'media',
                'ambiente': 'produção',
                'prioridade': 'media',
                'responsavel': usuarios['alice'],
                'coluna': colunas[2],  # Em Revisão
                'passos_reproducao': (
                    '1. Acessar sistema via smartphone\n'
                    '2. Abrir menu lateral\n'
                    '3. Tentar fechar o menu\n'
                    '4. Menu permanece aberto sobrepondo conteúdo'
                ),
                'prazo': timezone.now().date() + timedelta(days=3)
            },
            {
                'titulo': 'Performance lenta no dashboard',
                'descricao': 'Dashboard demora mais de 10s para carregar com muitos dados',
                'severidade': 'media',
                'ambiente': 'homologação',
                'prioridade': 'media',
                'responsavel': usuarios['carol'],
                'coluna': colunas[0],  # Backlog
                'passos_reproducao': (
                    '1. Acessar dashboard com usuário de teste\n'
                    '2. Aguardar carregamento completo\n'
                    '3. Tempo médio: 12-15 segundos'
                ),
                'prazo': timezone.now().date() + timedelta(days=10)
            }
        ]

        for idx, data in enumerate(bugs_data):
            bug = Bug.objects.create(
                titulo=data['titulo'],
                descricao=data['descricao'],
                severidade=data['severidade'],
                ambiente=data['ambiente'],
                prioridade=data['prioridade'],
                responsavel=data['responsavel'],
                coluna=data['coluna'],
                criado_por=usuarios['meira'],
                ordem=idx + len(features_data),
                passos_reproducao=data['passos_reproducao'],
                prazo=data['prazo']
            )
            items.append(bug)

        self.stdout.write(f'  ✓ {len(features_data)} features criadas')
        self.stdout.write(f'  ✓ {len(bugs_data)} bugs criados')
        return items

    def _criar_registros_hora(self, items, usuarios):
        """Cria registros de horas trabalhadas (se não existirem)"""
        self.stdout.write('⏱️  Criando/verificando registros de horas...')

        # Verificar se já existem registros
        if RegistroHora.objects.filter(usuario__in=usuarios.values()).exists():
            total_registros = RegistroHora.objects.filter(usuario__in=usuarios.values()).count()
            self.stdout.write(f'  ✓ {total_registros} registros de hora já existem')
            return

        registros_criados = 0

        # Feature concluída - documentação
        feature_doc = [item for item in items if 'Documentação' in item.titulo]
        if feature_doc:
            feature_doc = feature_doc[0]
            RegistroHora.objects.create(
                usuario=usuarios['bob'],
                feature=feature_doc,
                inicio=timezone.now() - timedelta(days=3, hours=8),
                fim=timezone.now() - timedelta(days=3, hours=4),
                descricao='Escrita da documentação básica da API'
            )
            registros_criados += 1

        # Bug em progresso - login
        bug_login = [item for item in items if 'login' in item.titulo]
        if bug_login:
            bug_login = bug_login[0]
            RegistroHora.objects.create(
                usuario=usuarios['bob'],
                bug=bug_login,
                inicio=timezone.now() - timedelta(hours=2),
                fim=timezone.now() - timedelta(minutes=30),
                descricao='Investigação inicial do problema'
            )
            registros_criados += 1

        # Feature em progresso - dashboard
        feature_dash = [item for item in items if 'Dashboard' in item.titulo]
        if feature_dash:
            feature_dash = feature_dash[0]
            RegistroHora.objects.create(
                usuario=usuarios['alice'],
                feature=feature_dash,
                inicio=timezone.now() - timedelta(days=1, hours=6),
                fim=timezone.now() - timedelta(days=1, hours=2),
                descricao='Implementação dos gráficos base'
            )
            RegistroHora.objects.create(
                usuario=usuarios['alice'],
                feature=feature_dash,
                inicio=timezone.now() - timedelta(hours=3),
                fim=None,  # Em andamento
                descricao='Ajustes de responsividade'
            )
            registros_criados += 2

        self.stdout.write(f'  ✓ {registros_criados} registros de hora criados')

    def _criar_comentarios(self, items, usuarios):
        """Cria comentários nos items (se não existirem)"""
        self.stdout.write('💬 Criando/verificando comentários...')

        # Verificar se já existem comentários
        if Comentario.objects.filter(usuario__in=usuarios.values()).exists():
            total_comentarios = Comentario.objects.filter(usuario__in=usuarios.values()).count()
            self.stdout.write(f'  ✓ {total_comentarios} comentários já existem')
            return

        comentarios_criados = 0

        # Comentários no bug de login
        bug_login = [item for item in items if 'login' in item.titulo]
        if bug_login:
            bug_login = bug_login[0]
            Comentario.objects.create(
                usuario=usuarios['meira'],
                bug=bug_login,
                texto='Prioridade alta! Vários clientes reportaram este problema.'
            )
            Comentario.objects.create(
                usuario=usuarios['bob'],
                bug=bug_login,
                texto='Identificado o problema: regex de validação não aceita formato de email. Trabalhando na correção.'
            )
            comentarios_criados += 2

        # Comentários na feature de dashboard
        feature_dash = [item for item in items if 'Dashboard' in item.titulo]
        if feature_dash:
            feature_dash = feature_dash[0]
            Comentario.objects.create(
                usuario=usuarios['vini'],
                feature=feature_dash,
                texto='Incluir gráfico de burndown e velocity do sprint atual.'
            )
            Comentario.objects.create(
                usuario=usuarios['alice'],
                feature=feature_dash,
                texto='Chart.js implementado. Faltam apenas os ajustes de cores para seguir a identidade visual.'
            )
            comentarios_criados += 2

        self.stdout.write(f'  ✓ {comentarios_criados} comentários criados')

    def _exibir_resumo(self):
        """Exibe resumo dos dados criados"""
        self.stdout.write('\n📊 RESUMO DO SEED:')
        self.stdout.write(f'  • Usuários: {Usuario.objects.count()}')
        self.stdout.write(f'  • Projetos: {Projeto.objects.count()}')
        self.stdout.write(f'  • Boards: {Board.objects.count()}')
        self.stdout.write(f'  • Colunas: {Coluna.objects.count()}')
        self.stdout.write(f'  • Features: {Feature.objects.count()}')
        self.stdout.write(f'  • Bugs: {Bug.objects.count()}')
        self.stdout.write(f'  • Registros de hora: {RegistroHora.objects.count()}')
        self.stdout.write(f'  • Comentários: {Comentario.objects.count()}')

        self.stdout.write('\n🔑 CREDENCIAIS DE ACESSO:')
        self.stdout.write('  • admin/admin123 (Administrador)')
        self.stdout.write('  • vini/vini123 (Gerente)')
        self.stdout.write('  • meira/meira123 (Gerente)')
        self.stdout.write('  • alice/alice123 (Funcionário)')
        self.stdout.write('  • bob/bob123 (Funcionário)')
        self.stdout.write('  • carol/carol123 (Funcionário)')