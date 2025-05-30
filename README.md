# 🚀 Vortex Board

Sistema Kanban profissional desenvolvido pela **Vórtex Startup** usando Django, WebSockets e Tailwind CSS.

## ✨ Funcionalidades

### 🎯 Board Kanban
- **Drag & Drop** em tempo real entre colunas
- **WebSockets** para colaboração simultânea
- **WIP Limits** configuráveis por coluna
- **Filtros** avançados por responsável, prioridade, tipo
- **Comentários** e **registros de hora** em cada item

### 🐛 Gestão de Bugs
- **Severidade** (baixa, média, alta, crítica)
- **Ambiente** de ocorrência
- **Passos para reprodução**
- Sistema de **pontuação** automática

### ✨ Gestão de Features  
- **Categorias** (UX/UI, Backend, Frontend, Infra, Docs)
- **Estimativa de horas**
- **Especificações** via URL
- Cálculo de **complexidade** baseado em horas

### 👥 Sistema de Usuários
- **3 níveis**: Admin, Gerente, Funcionário
- **Permissões** granulares por ação
- **Perfis** customizáveis com foto
- **Registro de horas** por usuário

### 📊 Relatórios e Métricas
- **Relatórios PDF** completos por projeto
- **Exportação CSV/Excel** com múltiplas abas
- **Dashboard** com métricas em tempo real
- **Burndown Chart** e velocity tracking
- **Distribuição de trabalho** por membro

## 🛠️ Tecnologias

- **Backend**: Django 4.2 + Django Channels (WebSockets)
- **Frontend**: Tailwind CSS + HTMX + Alpine.js
- **Banco**: PostgreSQL
- **Cache**: Redis
- **Relatórios**: ReportLab (PDF) + XlsxWriter (Excel)
- **Deploy**: Docker + AWS Lightsail

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.11+
- **PostgreSQL 15+** (mesmo banco dev/prod)
- Redis 7+ (opcional para WebSockets)
- Docker & Docker Compose (opcional)

### 1. Clonagem e Setup

```bash
# Clonar repositório
git clone https://github.com/vortex-startup/vortex-board.git
cd vortex-board

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências essenciais
pip install Django==4.2.8 django-environ==0.11.2 django-extensions==3.2.3 django-redis==5.4.0 dj-database-url==2.1.0 channels==4.0.0 django-htmx==1.17.2 Pillow==10.1.0 reportlab==4.0.7 psycopg2-binary==2.9.9

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações PostgreSQL
```

### 2. Configuração PostgreSQL

#### Windows (Automático):
```bash
# Executar script de setup automático
setup_windows.bat
```

#### Manual (Todas as plataformas):
```bash
# 1. Instalar PostgreSQL 15+
# Windows: https://www.postgresql.org/download/windows/
# macOS: brew install postgresql@15
# Ubuntu: sudo apt install postgresql-15

# 2. Configurar banco e usuário
python manage.py setup-db

# 3. Verificar .env com credenciais corretas
DB_NAME=vortex_board
DB_USER=vortex_user  
DB_PASSWORD=vortex123
DB_HOST=localhost
DB_PORT=5432
```

### 3. Executar Setup do Projeto

```bash
# Setup completo (migrações + seed + superuser)
python manage.py setup

# Ou manualmente:
python manage.py migrate
python manage.py collectstatic
python manage.py seed
```

### 4. Iniciar Servidor

```bash
# Desenvolvimento
python manage.py runserver

# Acesse: http://localhost:8000
# Login: admin / admin123
```

## 🐳 Docker

### Desenvolvimento com Docker Compose

```bash
# Subir todos os serviços
docker compose up -d

# Ver logs
docker compose logs -f web

# Executar comandos
docker compose exec web python manage.py shell
docker compose exec web python manage.py seed
```

### Produção

```bash
# Build da imagem
docker build -t vortex-board .

# Executar com variáveis de produção
docker run -d \
  --name vortex-board \
  -p 8000:8000 \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  vortex-board web
```

## 📁 Estrutura do Projeto

```
vortex-board/
├── apps/
│   ├── core/           # Usuários, projetos, modelos base
│   ├── board/          # Kanban, WebSockets, drag-drop  
│   └── relatorios/     # PDF, CSV, métricas
├── config/
│   ├── settings/       # Configurações por ambiente
│   ├── urls.py         # URLs principais
│   ├── wsgi.py         # WSGI para produção
│   └── asgi.py         # ASGI para WebSockets
├── templates/          # Templates Django
├── static/             # CSS, JS, imagens
├── docker/             # Configurações Docker
└── docs/               # Documentação
```

## 🎭 Conceitos POO Aplicados

### 1. **Encapsulamento**
```python
class Usuario(AbstractUser):
    # Atributo privado
    __senha_hash = models.CharField(max_length=128, editable=False)
    
    @property
    def senha_hash(self):
        """Getter encapsulado"""
        return self.__senha_hash
    
    def atualizar_senha_hash(self):
        """Método encapsulado"""
        if self.password:
            self.__senha_hash = hashlib.sha256(self.password.encode()).hexdigest()[:32]
```

### 2. **Herança e Polimorfismo**
```python
class ItemBase(models.Model):
    """Classe base abstrata"""
    class Meta:
        abstract = True
    
    @abstractmethod
    def calcular_pontos(self):
        pass

class Bug(ItemBase):
    """Implementação polimórfica"""
    def calcular_pontos(self):
        return 3 + bonus_severidade.get(self.severidade, 0)

class Feature(ItemBase):
    """Implementação polimórfica diferente"""
    def calcular_pontos(self):
        return 5 + ajuste_complexidade_horas(self.estimativa_horas)
```

### 3. **Abstração**
```python
class VortexPermissions:
    """Abstração do sistema de permissões"""
    
    @staticmethod
    def pode_editar_item(user, item):
        """Interface abstraída para verificação de permissões"""
        if user.tipo == 'admin':
            return True
        return item.criado_por == user or item.responsavel == user
```

## 🔧 Comandos Úteis

```bash
# Desenvolvimento
python manage.py setup           # Setup completo
python manage.py seed            # Popular com dados demo
python manage.py seed --clear    # Limpar e repopular
python manage.py shell_plus      # Shell avançado
python manage.py runserver_plus  # Servidor com extras

# Banco de dados
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell

# Testes
python manage.py test
pytest                          # Com coverage
pytest --cov=apps --cov-report=html

# Produção
python manage.py check --deploy
python manage.py collectstatic
python manage.py compress

# Backup e restore
python manage.py backup         # Backup JSON
python manage.py dumpdata > backup.json
python manage.py loaddata backup.json
```

## 🔒 Variáveis de Ambiente

### Obrigatórias
```bash
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port/db
```

### Opcionais
```bash
SENTRY_DSN=https://...          # Error tracking
EMAIL_HOST=smtp.gmail.com       # Email real
AWS_S3_BUCKET=bucket-name       # Arquivos estáticos
SLACK_WEBHOOK=https://...       # Notificações Slack
```

## 📊 Deploy AWS Lightsail

### 1. Criar Container Service
```bash
# Via AWS CLI
aws lightsail create-container-service \
  --service-name vortex-board \
  --power micro \
  --scale 1
```

### 2. Deploy da Aplicação
```bash
# Push da imagem
aws lightsail push-container-image \
  --service-name vortex-board \
  --label vortex-web \
  --image vortex-board:latest

# Deploy do serviço
aws lightsail create-container-service-deployment \
  --service-name vortex-board \
  --containers file://containers.json \
  --public-endpoint file://public-endpoint.json
```

### 3. Configurar Banco RDS
```bash
# Criar instância PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier vortex-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username vortex_user \
  --master-user-password SUA_SENHA_AQUI \
  --allocated-storage 20
```

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Testes com coverage
pytest --cov=apps --cov-report=html --cov-report=term

# Testes específicos
python manage.py test apps.core.tests.test_models
python manage.py test apps.board.tests.test_websocket

# Testes de integração
python manage.py test apps.relatorios.tests.test_pdf_generation
```

## 📈 Monitoramento

### Logs
```bash
# Ver logs em tempo real
tail -f logs/vortex.log

# Logs estruturados
grep "ERROR" logs/vortex.log | jq .

# Logs do Docker
docker compose logs -f web
```

### Health Check
```bash
# Endpoint de status
curl http://localhost:8000/health/

# Resposta esperada:
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "version": "0.1.0"
}
```

## 🤝 Contribuição

1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'feat(board): adicionar drag-and-drop'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um **Pull Request**

### Padrões de Commit
```
feat(escopo): descrição         # Nova funcionalidade
fix(escopo): descrição          # Correção de bug
docs(escopo): descrição         # Documentação
style(escopo): descrição        # Formatação
refactor(escopo): descrição     # Refatoração
test(escopo): descrição         # Testes
chore(escopo): descrição        # Manutenção
```

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) untuk detalhes.

## 👨‍💻 Autores

- **Vini** - *Arquitetura e Backend* - [@vini](https://github.com/vini)
- **Meira** - *Frontend e UX* - [@meira](https://github.com/meira)

## 🙏 Agradecimentos

- Django Community
- Tailwind CSS Team
- HTMX Project
- Alpine.js Team

---

**Vórtex Startup** © 2024 - Sistema Kanban Profissional