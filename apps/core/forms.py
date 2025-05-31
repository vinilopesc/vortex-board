# apps/core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import Usuario, Projeto


class LoginForm(forms.Form):
    """Formulário de login customizado"""

    username = forms.CharField(
        label='Usuário ou Email',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Seu usuário ou email',
            'autofocus': True
        })
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Sua senha'
        })
    )

    lembrar_me = forms.BooleanField(
        label='Lembrar-me',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600'
        })
    )


class RegistroEmpresaForm(forms.ModelForm):
    """Formulário de registro de nova empresa"""

    nome_empresa = forms.CharField(
        label='Nome da Empresa',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Ex: Vórtex Startup Ltda'
        })
    )

    password = forms.CharField(
        label='Senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )

    confirmar_password = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Digite a senha novamente'
        })
    )

    aceito_termos = forms.BooleanField(
        label='Aceito os termos de uso e política de privacidade',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600'
        })
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'telefone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Nome de usuário único'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'email@empresa.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Seu nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Seu sobrenome'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': '(11) 99999-9999'
            }),
        }

    def clean_confirmar_password(self):
        """Valida se senhas coincidem"""
        password = self.cleaned_data.get('password')
        confirmar_password = self.cleaned_data.get('confirmar_password')

        if password and confirmar_password and password != confirmar_password:
            raise ValidationError("As senhas não coincidem")

        return confirmar_password

    def clean_email(self):
        """Valida se email já não está em uso"""
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError("Este email já está em uso")
        return email

    def clean_username(self):
        """Valida se username já não está em uso"""
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError("Este nome de usuário já está em uso")
        return username


class RecuperarSenhaForm(forms.Form):
    """Formulário para solicitar recuperação de senha"""

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Digite seu email cadastrado'
        })
    )


class RedefinirSenhaForm(forms.Form):
    """Formulário para redefinir senha com token"""

    nova_senha = forms.CharField(
        label='Nova Senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )

    confirmar_nova_senha = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Digite a senha novamente'
        })
    )

    def clean_confirmar_nova_senha(self):
        """Valida se senhas coincidem"""
        nova_senha = self.cleaned_data.get('nova_senha')
        confirmar_nova_senha = self.cleaned_data.get('confirmar_nova_senha')

        if nova_senha and confirmar_nova_senha and nova_senha != confirmar_nova_senha:
            raise ValidationError("As senhas não coincidem")

        return confirmar_nova_senha


# Mantendo os demais forms existentes...
class UsuarioUpdateForm(forms.ModelForm):
    """Formulário de atualização de perfil"""

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefone', 'foto']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': '(00) 00000-0000'
            }),
            'foto': forms.FileInput(attrs={
                'class': 'form-input w-full px-4 py-2',
                'accept': 'image/*'
            })
        }


class AlterarSenhaForm(PasswordChangeForm):
    """Formulário de alteração de senha customizado"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customizar widgets
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Senha atual'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Nova senha'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': 'Confirme a nova senha'
        })


class ProjetoForm(forms.ModelForm):
    """Formulário para criar/editar projetos"""

    class Meta:
        model = Projeto
        fields = ['nome', 'cliente', 'descricao', 'membros', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Nome do projeto'
            }),
            'cliente': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Nome do cliente'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-textarea w-full px-4 py-2 border rounded-lg',
                'rows': 4,
                'placeholder': 'Descrição do projeto...'
            }),
            'membros': forms.SelectMultiple(attrs={
                'class': 'form-select w-full px-4 py-2 border rounded-lg',
                'size': 6
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-4 w-4 text-blue-600'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Ordenar membros por nome
        self.fields['membros'].queryset = Usuario.objects.filter(
            is_active=True
        ).order_by('first_name', 'username')

        # Se for criação, adicionar o usuário atual como membro
        if not self.instance.pk and user:
            self.fields['membros'].initial = [user]

    def clean_nome(self):
        """Validação customizada para nome único por cliente"""
        nome = self.cleaned_data['nome']
        cliente = self.cleaned_data.get('cliente')

        # Verificar se já existe projeto com mesmo nome para o cliente
        qs = Projeto.objects.filter(nome=nome, cliente=cliente)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(
                f'Já existe um projeto "{nome}" para o cliente {cliente}.'
            )

        return nome


class FiltroProjetoForm(forms.Form):
    """Formulário para filtrar projetos no painel"""

    ORDENACAO_CHOICES = [
        ('-criado_em', 'Mais recentes'),
        ('criado_em', 'Mais antigos'),
        ('nome', 'Nome (A-Z)'),
        ('-nome', 'Nome (Z-A)'),
        ('cliente', 'Cliente (A-Z)'),
    ]

    busca = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input px-4 py-2 border rounded-lg',
            'placeholder': 'Buscar projetos...'
        })
    )

    apenas_ativos = forms.BooleanField(
        required=False,
        initial=True,
        label='Apenas ativos',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600'
        })
    )

    ordenacao = forms.ChoiceField(
        choices=ORDENACAO_CHOICES,
        required=False,
        initial='-criado_em',
        widget=forms.Select(attrs={
            'class': 'form-select px-4 py-2 border rounded-lg'
        })
    )