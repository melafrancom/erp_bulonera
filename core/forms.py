from django import forms

# from Local apps
from .models import RegistrationRequest, User  # Agregado User


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label='Usuario o Email',
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
            'placeholder': 'Usuario o Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
            'placeholder': 'Contraseña'
        })
    )


class RegistrationRequestForm(forms.ModelForm):
    class Meta:
        model = RegistrationRequest
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'reason', 'requested_role']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'Usuario deseado'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'tu@email.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'Apellido'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': '+54 9 ...'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': '¿Por qué necesitas acceso al sistema?',
                'rows': 4
            }),
            'requested_role': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
            }),
        }
        labels = {
            'username': 'Usuario',
            'email': 'Email',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'phone': 'Teléfono (opcional)',
            'reason': 'Motivo de solicitud',
            'requested_role': 'Rol solicitado',
        }
    
    def clean_username(self):
        username = self.cleaned_data['username']
        # Verificar si ya existe un usuario activo (no eliminado) con este username
        if User.all_objects.filter(username=username, deleted_at__isnull=True).exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso.')
        # Verificar si ya hay una solicitud pendiente con este username
        if RegistrationRequest.objects.filter(username=username, status='pending').exists():
            raise forms.ValidationError('Ya existe una solicitud pendiente con este nombre de usuario.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Verificar si ya existe un usuario activo (no eliminado) con este email
        if User.all_objects.filter(email__iexact=email, deleted_at__isnull=True).exists():
            raise forms.ValidationError('Este email ya está en uso por un usuario activo.')
        # Verificar si ya hay una solicitud pendiente con este email
        if RegistrationRequest.objects.filter(email__iexact=email, status='pending').exists():
            raise forms.ValidationError('Ya existe una solicitud pendiente con este email.')
        return email


class UserEditForm(forms.ModelForm):
    """Formulario para editar perfil del usuario (sin cambiar username/role)"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'Apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
                'placeholder': 'tu@email.com'
            }),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Email',
        }