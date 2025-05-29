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
        """Remove todos os dados exceto superusuário"""
        Comentario.objects.all().delete()
        RegistroHora.objects.all().delete()
        Bug.objects.all().delete()
        Feature.objects.all().delete()
        Coluna.objects.all().delete()
        Board.objects.all().delete()
        Projeto.objects.all().delete()
        Usuario.objects.exclude(is_superuser=True).delete()

    def _criar_usuarios(self):
        """Cria usuários com diferentes níveis de acesso"""
        self.stdout.write('👥 Criando usuários...')

        usuarios = {}

        # Admin
        usuarios['admin'] = Usuario.objects.create_user(
            username='admin',
            email='admin@vortex.com.br',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema',
            tipo='admin',
            is_staff=True,
            is_superuser=True
        )

        # Gerente - Vini
        usuarios['vini'] = Usuario.objects.create_user(
            username='vini',
            email='vini@vortex.com.br',
            password='vini123',
            first_name='Vinícius',
            last_name='Oliveira',
            tipo='gerente',
            telefone='(31) 98765-4321'
        )

        # Gerente - Meira
        usuarios['meira'] = Usuario.objects.create_user(
            username='meira',
            email='meira@vortex.com.br',
            password='meira123',
            first_name='João',
            last_name='Meira',
            tipo='gerente',
            telefone='(31) 98765-4322'
        )

        # Funcionários
        usuarios['alice'] = Usuario.objects.create_user(
            username='alice',
            email='alice@vortex.com.br',
            password='alice123',
            first_name='Alice',
            last_name='Santos',
            tipo='funcionario',
            telefone='(31) 98765-4323'
        )

        usuarios['bob'] = Usuario.objects.create_user(
            username='bob',
            email='bob@vortex.com.br',
            password='bob123',
            first_name='Roberto',
            last_name='Silva',
            tipo='funcionario',
            telefone='(31) 98765-4324'
        )

        usuarios['carol'] = Usuario.objects.create_user(
            username='carol',
            email='carol@vortex.com.br',
            password='carol123',
            first_name='Carolina',
            last_name='Ferreira',
            tipo='funcionario',
            telefone='(31) 98765-4325'
        )

        self.stdout.write(f'  ✓ {len(usuarios)} usuários criados')
        return usuarios

    def _criar_projeto_demo(self, usuarios):
        """Cria projeto de demonstração"""
        self.stdout.write('📁 Criando projeto demo...')

        projeto = Projeto.objects.create(
            nome='Demo Vortex',
            cliente='Cliente Exemplo S.A.',
            descricao=(
                'Projeto de demonstração do sistema Vortex Board. '
                'Este projeto contém exemplos de todas as funcionalidades '
                'disponíveis no sistema.'
            ),
            criado_por=usuarios['vini']
        )

        # Adiciona todos os usuários como membros
        projeto.membros.set(usuarios.values())

        self.stdout.write('  ✓ Projeto demo criado')
        return projeto

    def _criar_board_com_colunas(self, projeto):
        """Cria board com colunas padrão"""
        self.stdout.write('📋 Criando board e colunas...')

        board = Board.objects.create(
            titulo='Sprint 1 - MVP',
            projeto=projeto,
            descricao='Primeira sprint do projeto Demo Vortex'
        )

        # Colunas com configurações específicas
        colunas_config = [
            ('Backlog', '#6B7280', 0),  # Cinza
            ('Em Progresso', '#3B82F6', 3),  # Azul, WIP limit 3
            ('Em Revisão', '#F59E0B', 2),  # Amarelo, WIP limit 2
            ('Concluído', '#10B981', 0),  # Verde
        ]

        for idx, (titulo, cor, wip) in enumerate(colunas_config):
            Coluna.objects.create(
                titulo=titulo,
                board=board,
                ordem=idx,
                cor=cor,
                limite_wip=wip
            )

        self.stdout.write('  ✓ Board com 4 colunas criado')
        return board

    def _criar_items_demo(self, board, usuarios):
        """Cria bugs e features de demonstração"""
        self.stdout.write('🎯 Criando items (bugs e features)...')

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
        """Cria registros de horas trabalhadas"""
        self.stdout.write('⏱️  Criando registros de horas...')

        registros_criados = 0

        # Feature concluída - documentação
        feature_doc = [item for item in items if 'Documentação' in item.titulo][0]
        RegistroHora.objects.create(
            usuario=usuarios['bob'],
            feature=feature_doc,
            inicio=timezone.now() - timedelta(days=3, hours=8),
            fim=timezone.now() - timedelta(days=3, hours=4),
            descricao='Escrita da documentação básica da API'
        )
        registros_criados += 1

        # Bug em progresso - login
        bug_login = [item for item in items if 'login' in item.titulo][0]
        RegistroHora.objects.create(
            usuario=usuarios['bob'],
            bug=bug_login,
            inicio=timezone.now() - timedelta(hours=2),
            fim=timezone.now() - timedelta(minutes=30),
            descricao='Investigação inicial do problema'
        )
        registros_criados += 1

        # Feature em progresso - dashboard
        feature_dash = [item for item in items if 'Dashboard' in item.titulo][0]
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
        """Cria comentários nos items"""
        self.stdout.write('💬 Criando comentários...')

        comentarios_criados = 0

        # Comentários no bug de login
        bug_login = [item for item in items if 'login' in item.titulo][0]
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
        feature_dash = [item for item in items if 'Dashboard' in item.titulo][0]
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