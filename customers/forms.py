from django import forms
from django.core.exceptions import ValidationError
from .models import Customer, CustomerSegment, CustomerNote
import re


class CustomerForm(forms.ModelForm):
    """
    Form for creating and updating customers.
    """
    
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'business_name', 'trade_name',
            'cuit_cuil', 'tax_condition',
            'email', 'phone', 'mobile', 'website', 'contact_person',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code', 'billing_country',
            'customer_segment', # 'price_list',
            'payment_term', 'credit_limit', 'discount_percentage',
            'allow_credit', 'notes'
        ]
        widgets = {
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razón Social'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Comercial (opcional)'}),
            'cuit_cuil': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XX-XXXXXXXX-X'}),
            'tax_condition': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@ejemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0291-4XXXXXX'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '291-15XXXXXX'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_address': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_city': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_state': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_country': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_segment': forms.Select(attrs={'class': 'form-select'}),
            # 'price_list': forms.Select(attrs={'class': 'form-select'}),
            'payment_term': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'allow_credit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_cuit_cuil(self):
        """
        Validate and format CUIT/CUIL.
        """
        cuit = self.cleaned_data.get('cuit_cuil', '')
        
        # Remove spaces
        cuit = cuit.replace(' ', '')
        
        # If it doesn't have dashes, try to format it
        if '-' not in cuit and len(cuit) == 11 and cuit.isdigit():
            cuit = f"{cuit[0:2]}-{cuit[2:10]}-{cuit[10]}"
        
        # Validate format
        pattern = r'^\d{2}-\d{8}-\d{1}$'
        if not re.match(pattern, cuit):
            raise ValidationError('El CUIT/CUIL debe tener el formato XX-XXXXXXXX-X')
        
        return cuit
        
        # Validate checksum
        from common.utils import validate_cuit
        if not validate_cuit(cuit):
            raise ValidationError('El CUIT/CUIL no es válido (dígito verificador incorrecto).')
        
        return cuit
    
    def clean(self):
        """
        Additional validation.
        """
        cleaned_data = super().clean()
        allow_credit = cleaned_data.get('allow_credit')
        credit_limit = cleaned_data.get('credit_limit')
        
        # If credit is allowed, credit limit must be > 0
        if allow_credit and (not credit_limit or credit_limit <= 0):
            raise ValidationError({
                'credit_limit': 'El límite de crédito debe ser mayor a 0 si se permite crédito.'
            })
        
        return cleaned_data


class CustomerSearchForm(forms.Form):
    """
    Form for searching customers.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, CUIT, email...'
        })
    )
    segment = forms.ModelChoiceField(
        queryset=CustomerSegment.objects.filter(is_active=True),
        required=False,
        empty_label='Todos los segmentos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    customer_type = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + Customer.CUSTOMER_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CustomerImportForm(forms.Form):
    """
    Form for importing customers from Excel.
    """
    file = forms.FileField(
        label='Archivo Excel',
        help_text='Seleccione un archivo .xlsx con los datos de clientes',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )
    update_existing = forms.BooleanField(
        label='Actualizar clientes existentes',
        required=False,
        initial=True,
        help_text='Si está marcado, los clientes existentes (por CUIT) serán actualizados',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_file(self):
        """
        Validate uploaded file.
        """
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file extension
            if not file.name.endswith(('.xlsx', '.xls')):
                raise ValidationError('El archivo debe ser un formato Excel (.xlsx o .xls)')
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('El archivo no puede superar los 5MB')
        
        return file


class CustomerSegmentForm(forms.ModelForm):
    """
    Form for creating and updating customer segments.
    """
    
    class Meta:
        model = CustomerSegment
        fields = ['name', 'description', 'color', 'discount_percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'value': '#3B82F6'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


class CustomerNoteForm(forms.ModelForm):
    """
    Form for adding notes to customers.
    """
    
    class Meta:
        model = CustomerNote
        fields = ['title', 'content', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
