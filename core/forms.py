from django import forms

#from Local apps
from .models import RegistrationRequest


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Usuario',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Contraseña'
        })
    )

class RegistrationRequestForm(forms.ModelForm):
    class Meta:
        model = RegistrationRequest
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'reason', 'requested_role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Usuario deseado'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'tu@email.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Apellido'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+54 9 ...'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-input', 
                'placeholder': '¿Por qué necesitas acceso al sistema?',
                'rows': 4
            }),
            'requested_role': forms.Select(attrs={'class': 'form-select'}),
        }