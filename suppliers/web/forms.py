"""
Django Forms para la app Suppliers.
"""
from django import forms
from suppliers.models import Supplier, SupplierTag


class SupplierForm(forms.ModelForm):
    """Formulario para crear/editar proveedores."""

    class Meta:
        model = Supplier
        fields = [
            'business_name', 'trade_name', 'cuit', 'tax_condition',
            'email', 'phone', 'mobile', 'website',
            'address', 'city', 'state', 'zip_code',
            'bank_name', 'cbu', 'bank_alias',
            'contact_person', 'contact_email', 'contact_phone',
            'payment_term', 'payment_day_of_month',
            'early_payment_discount', 'delivery_days',
            'notes', 'last_price_list_date',
            'tags', 'is_active',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razón Social'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Comercial'}),
            'cuit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XX-XXXXXXXX-X'}),
            'tax_condition': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cbu': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_alias': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_term': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'payment_day_of_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 28}),
            'early_payment_discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'delivery_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'last_price_list_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tags': forms.CheckboxSelectMultiple(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_cuit(self):
        """Valida CUIT con dígito verificador."""
        from common.utils import validate_cuit

        cuit = self.cleaned_data.get('cuit', '')
        clean_value = cuit.replace('-', '')
        if not validate_cuit(clean_value):
            raise forms.ValidationError(
                "El CUIT no es válido (dígito verificador incorrecto)."
            )
        return cuit
