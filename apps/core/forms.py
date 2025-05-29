# apps/core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import Usuario, Projeto


class LoginForm(forms.Form):
    """Formulário de login customizado"""

    username = forms.CharField(
        label='Usuário',
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


class UsuarioCreationForm(UserCreationForm):
    """Formulário de criação de usuário customizado"""

    tipo = forms.ChoiceField(
        choices=Usuario.TIPO_USUARIO_CHOICES,
        label='Tipo de Usuário',
        widget=forms.Select(attrs={
            'class': 'form-select w-full px-4 py-2 border rounded-lg'
        })
    )

    telefone = forms.CharField(
        max_length=20,
        required=False,
        label='Telefone',
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border rounded-lg',
            'placeholder': '(00) 00000-0000'
        })
    )

    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name',
                  'tipo', 'telefone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input w-full px-4 py-2 border rounded-lg'
            }),
        }


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