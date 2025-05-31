# apps/core/auth_service.py

"""
Serviço de Autenticação - Encapsula toda lógica de auth do sistema
Aplica princípios de encapsulamento para manter código organizado e seguro
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import models  # ← ESTA ERA A IMPORTAÇÃO FALTANDO!
from typing import Optional, Tuple, Dict
from .models import Usuario


class AuthenticationService:
    """
    Serviço encapsulado para gerenciar autenticação

    Princípios aplicados:
    - Encapsulamento: Métodos privados protegem lógica interna
    - Responsabilidade única: Cada método tem uma função específica
    - Abstração: Interface simples para operações complexas
    """

    def __init__(self):
        # Atributos privados - encapsulados
        self._max_login_attempts = 5
        self._lockout_duration_minutes = 15
        self._password_reset_timeout_hours = 2

    def criar_usuario_empresa(self, dados_empresa: Dict) -> Tuple[bool, str, Optional[Usuario]]:
        """
        Cria novo usuário empresa com validações encapsuladas

        Args:
            dados_empresa: Dict com dados do usuário/empresa

        Returns:
            Tuple[sucesso, mensagem, usuario_criado]
        """
        try:
            # Validar dados de entrada
            validacao_ok, erro_validacao = self._validar_dados_empresa(dados_empresa)
            if not validacao_ok:
                return False, erro_validacao, None

            # Verificar se usuário já existe
            if self._usuario_existe(dados_empresa['username'], dados_empresa['email']):
                return False, "Usuário ou email já cadastrado no sistema", None

            # Criar usuário com senha criptografada
            usuario = self._criar_usuario_seguro(dados_empresa)

            # Enviar email de boas-vindas (método privado)
            self._enviar_email_boas_vindas(usuario)

            return True, "Usuário criado com sucesso!", usuario

        except Exception as e:
            # Em desenvolvimento, mostre o erro real para debug
            if settings.DEBUG:
                return False, f"Erro interno: {str(e)}", None
            else:
                # Em produção, mensagem genérica por segurança
                return False, "Erro interno do sistema. Tente novamente.", None

    def fazer_login(self, request, username: str, password: str, lembrar_me: bool = False) -> Tuple[bool, str]:
        """
        Realiza login com verificações de segurança encapsuladas

        Args:
            request: Request do Django
            username: Nome de usuário ou email
            password: Senha
            lembrar_me: Se deve manter sessão ativa

        Returns:
            Tuple[sucesso, mensagem]
        """
        # Verificar se conta está bloqueada
        if self._conta_esta_bloqueada(username):
            return False, "Conta temporariamente bloqueada por muitas tentativas incorretas"

        # Tentar autenticar
        usuario = self._autenticar_usuario(username, password)

        if usuario:
            # Login bem-sucedido
            login(request, usuario)

            # Configurar sessão se lembrar_me
            if lembrar_me:
                self._configurar_sessao_persistente(request)

            # Resetar tentativas de login
            self._resetar_tentativas_login(username)

            # Atualizar último acesso
            self._atualizar_ultimo_acesso(usuario)

            return True, f"Bem-vindo, {usuario.get_full_name() or usuario.username}!"

        else:
            # Login falhou - registrar tentativa
            self._registrar_tentativa_falha(username)
            return False, "Credenciais inválidas"

    def fazer_logout(self, request) -> bool:
        """Realiza logout seguro"""
        try:
            logout(request)
            return True
        except Exception:
            return False

    def iniciar_recuperacao_senha(self, email: str) -> Tuple[bool, str]:
        """
        Inicia processo de recuperação de senha

        Args:
            email: Email do usuário

        Returns:
            Tuple[sucesso, mensagem]
        """
        try:
            usuario = Usuario.objects.get(email=email, is_active=True)

            # Gerar token seguro
            token = self._gerar_token_recuperacao(usuario)

            # Enviar email com link
            sucesso_email = self._enviar_email_recuperacao(usuario, token)

            if sucesso_email:
                return True, "Email de recuperação enviado com sucesso"
            else:
                return False, "Erro ao enviar email. Tente novamente."

        except Usuario.DoesNotExist:
            # Por segurança, não revelar se email existe
            return True, "Se o email existir, você receberá instruções de recuperação"

    def validar_token_recuperacao(self, token: str, novo_password: str) -> Tuple[bool, str]:
        """
        Valida token e redefine senha

        Args:
            token: Token de recuperação
            novo_password: Nova senha

        Returns:
            Tuple[sucesso, mensagem]
        """
        try:
            # Decodificar token
            usuario = self._decodificar_token_recuperacao(token)
            if not usuario:
                return False, "Token inválido ou expirado"

            # Validar nova senha
            if not self._validar_senha(novo_password):
                return False, "Senha deve ter pelo menos 8 caracteres"

            # Redefinir senha
            usuario.set_password(novo_password)
            usuario.save()

            return True, "Senha redefinida com sucesso!"

        except Exception as e:
            return False, "Erro ao processar token"

    # =================== MÉTODOS PRIVADOS (ENCAPSULADOS) ===================

    def _validar_dados_empresa(self, dados: Dict) -> Tuple[bool, str]:
        """Valida dados de entrada para criação de empresa"""
        campos_obrigatorios = ['username', 'email', 'password', 'nome_empresa', 'first_name']

        for campo in campos_obrigatorios:
            if not dados.get(campo, '').strip():
                return False, f"Campo {campo} é obrigatório"

        # Validar email básico
        email = dados['email']
        if '@' not in email or '.' not in email.split('@')[-1]:
            return False, "Email inválido"

        # Validar senha
        if not self._validar_senha(dados['password']):
            return False, "Senha deve ter pelo menos 8 caracteres"

        # Validar username (sem espaços e caracteres especiais)
        username = dados['username']
        if ' ' in username or len(username) < 3:
            return False, "Nome de usuário deve ter pelo menos 3 caracteres e não conter espaços"

        return True, ""

    def _validar_senha(self, password: str) -> bool:
        """Valida força da senha"""
        return len(password) >= 8

    def _usuario_existe(self, username: str, email: str) -> bool:
        """
        Verifica se usuário já existe

        Agora com a importação correta do models para usar Q()
        """
        return Usuario.objects.filter(
            models.Q(username=username) | models.Q(email=email)
        ).exists()

    def _criar_usuario_seguro(self, dados: Dict) -> Usuario:
        """
        Cria usuário com configurações seguras e isolamento por empresa

        IMPORTANTE: Cada usuário criado automaticamente fica isolado
        na sua própria empresa (tenant)
        """
        usuario = Usuario.objects.create_user(
            username=dados['username'],
            email=dados['email'],
            password=dados['password'],  # Django já faz hash automaticamente
            first_name=dados['first_name'],
            last_name=dados.get('last_name', ''),
            telefone=dados.get('telefone', ''),
            tipo='admin',  # Primeiro usuário de cada empresa é admin
            empresa=dados['nome_empresa']  # ← CAMPO FUNDAMENTAL PARA ISOLAMENTO!
        )
        return usuario

    def _autenticar_usuario(self, username: str, password: str) -> Optional[Usuario]:
        """Autentica usuário (username ou email)"""
        # Tentar por username primeiro
        usuario = authenticate(username=username, password=password)

        if not usuario:
            # Tentar por email se username falhar
            try:
                user_obj = Usuario.objects.get(email=username, is_active=True)
                usuario = authenticate(username=user_obj.username, password=password)
            except Usuario.DoesNotExist:
                pass

        return usuario

    def _conta_esta_bloqueada(self, username: str) -> bool:
        """Verifica se conta está bloqueada por tentativas"""
        # TODO: Implementar sistema de cache para tentativas
        # Por enquanto, sempre permitir (implementar em próxima versão)
        return False

    def _registrar_tentativa_falha(self, username: str):
        """Registra tentativa de login falhada"""
        # TODO: Implementar com Redis/Cache
        # Por enquanto apenas log
        if settings.DEBUG:
            print(f"⚠️ Tentativa de login falhada para: {username}")

    def _resetar_tentativas_login(self, username: str):
        """Reseta contador de tentativas"""
        # TODO: Implementar com Redis/Cache
        pass

    def _configurar_sessao_persistente(self, request):
        """Configura sessão para durar mais tempo"""
        request.session.set_expiry(86400 * 30)  # 30 dias

    def _atualizar_ultimo_acesso(self, usuario: Usuario):
        """Atualiza timestamp do último acesso"""
        usuario.last_login = timezone.now()
        usuario.save(update_fields=['last_login'])

    def _gerar_token_recuperacao(self, usuario: Usuario) -> str:
        """Gera token seguro para recuperação"""
        timestamp = int(timezone.now().timestamp())
        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        return f"{uid}-{token}-{timestamp}"

    def _decodificar_token_recuperacao(self, token: str) -> Optional[Usuario]:
        """Decodifica e valida token de recuperação"""
        try:
            parts = token.split('-')
            if len(parts) != 3:
                return None

            uid, token_part, timestamp = parts

            # Verificar se não expirou (2 horas)
            token_time = int(timestamp)
            now = int(timezone.now().timestamp())
            if now - token_time > (self._password_reset_timeout_hours * 3600):
                return None

            # Decodificar usuário
            user_id = urlsafe_base64_decode(uid).decode()
            usuario = Usuario.objects.get(pk=user_id)

            # Validar token
            if default_token_generator.check_token(usuario, token_part):
                return usuario

            return None

        except Exception:
            return None


    def _enviar_email_boas_vindas(self, usuario: Usuario):
        """
        Envia email de boas-vindas para primeiro usuário de uma empresa

        Este método foi ajustado para a filosofia de "sistema virgem":
        - Celebra que esta é realmente a primeira empresa no sistema
        - Não faz referência a dados de exemplo ou demonstração
        """
        try:
            # Verificar se esta é realmente a primeira empresa no sistema
            total_empresas = Usuario.objects.values('empresa').distinct().count()

            if total_empresas == 1:
                # Esta é a primeira empresa no sistema!
                subject = f'Bem-vindo ao Vortex Board - Primeira Empresa Registrada!'
                message = f"""
    Parabéns {usuario.first_name}!

    Você acabou de registrar a PRIMEIRA empresa no sistema Vortex Board!

    🎉 Empresa: {usuario.empresa}
    👤 Administrador: {usuario.get_full_name()}
    📧 Email: {usuario.email}

    Seu sistema está completamente novo e pronto para uso.
    Você pode começar criando seus primeiros projetos e
    convidando sua equipe.

    Acesse o sistema e comece a organizar seus projetos!

    Atenciosamente,
    Sistema Vortex Board
                """
            else:
                # Empresa adicional
                subject = f'Bem-vindo ao Vortex Board, {usuario.empresa}!'
                message = f"""
    Olá {usuario.first_name}!

    Sua empresa "{usuario.empresa}" foi registrada com sucesso no Vortex Board!

    👤 Administrador: {usuario.get_full_name()}
    📧 Email: {usuario.email}

    Seus dados estão completamente isolados e seguros.
    Apenas membros da sua empresa podem ver seus projetos.

    Comece criando seus projetos e organizando sua equipe!

    Atenciosamente,
    Sistema Vortex Board
                """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=True
            )
        except Exception as e:
            if settings.DEBUG:
                print(f"⚠️ Erro ao enviar email de boas-vindas: {e}")

    def _enviar_email_recuperacao(self, usuario: Usuario, token: str) -> bool:
        """Envia email com link de recuperação"""
        try:
            # Construir URL absoluta
            # TODO: Em produção, usar domínio real
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            link_recuperacao = f"{base_url}/redefinir-senha/{token}/"

            subject = 'Recuperação de Senha - Vortex Board'
            message = f"""
Olá {usuario.first_name},

Você solicitou a recuperação de senha para sua conta no Vortex Board.

Clique no link abaixo para redefinir sua senha:
{link_recuperacao}

Este link expira em 2 horas por motivos de segurança.

Se você não solicitou esta recuperação, ignore este email.

Atenciosamente,
Equipe Vortex Board
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False
            )
            return True

        except Exception as e:
            # Log do erro se estivermos em desenvolvimento
            if settings.DEBUG:
                print(f"⚠️ Erro ao enviar email de recuperação: {e}")
            return False


# Instância global do serviço (Singleton pattern)
auth_service = AuthenticationService()