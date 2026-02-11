from django.test import TestCase
from common.utils import validate_cuit, format_cuit, normalize_phone


class CUITValidatorTests(TestCase):
    """Tests específicos para validación de CUIT/CUIL usando common.utils"""
    
    def test_cuit_valido_persona_fisica(self):
        """TC-V001: CUIT de persona física válido"""
        self.assertTrue(validate_cuit('20-11111111-2'))
    
    def test_cuit_valido_persona_juridica(self):
        """TC-V002: CUIT de persona jurídica válido"""
        self.assertTrue(validate_cuit('30-70707070-2'))
    
    def test_cuil_valido_mujer(self):
        """TC-V003: CUIL de mujer válido"""
        self.assertTrue(validate_cuit('27-22222222-8'))
    
    def test_cuit_invalido_digito_verificador(self):
        """TC-V004: CRÍTICO - Detectar CUIT con dígito verificador incorrecto"""
        self.assertFalse(validate_cuit('20-12345678-0'))  # Último dígito incorrecto
    
    def test_cuit_invalido_longitud(self):
        """TC-V005: CUIT con longitud incorrecta"""
        self.assertFalse(validate_cuit('20-1234567-8'))  # Faltan dígitos
        self.assertFalse(validate_cuit('123'))
    
    def test_cuit_invalido_caracteres_no_numericos(self):
        """TC-V006: CUIT con caracteres no numéricos"""
        self.assertFalse(validate_cuit('20-ABCDEFGH-9'))
    
    def test_format_cuit_agrega_guiones(self):
        """TC-V007: Formateo automático de CUIT"""
        # La función format_cuit de utils.py retorna string con guiones
        formatted = format_cuit('20123456789')
        self.assertEqual(formatted, '20-12345678-9')
    
    def test_format_cuit_ya_formateado(self):
        """TC-V008: CUIT ya formateado se mantiene"""
        formatted = format_cuit('20-12345678-9')
        self.assertEqual(formatted, '20-12345678-9')


class PhoneValidatorTests(TestCase):
    """Tests para normalización de teléfonos argentinos"""
    
    def test_normalize_phone_formato_completo(self):
        """TC-V009: Normalizar teléfono con formato completo"""
        # La función de utils no es tan agresiva si ya tiene +54
        normalized = normalize_phone('+54 9 362 4567890')
        # normalize_phone solo quita no-dígitos salvo +. 
        # '+54 9 362 4567890' -> '+5493624567890'
        self.assertEqual(normalized, '+5493624567890')
    
    def test_normalize_phone_sin_codigo_pais(self):
        """TC-V010: Agregar código de país automáticamente"""
        normalized = normalize_phone('0362-4567890')
        # Remueve 0 inicial, agrega +54
        self.assertTrue(normalized.startswith('+54'))
        self.assertEqual(normalized, '+543624567890') 
        # Nota: La implementación en utils.py puede variar, 
        # asumimos que remueve el 0 y agrega +54.
    
    def test_normalize_phone_elimina_espacios(self):
        """TC-V011: Eliminar espacios y caracteres especiales"""
        normalized = normalize_phone('0362 - 456 - 7890')
        self.assertNotIn(' ', normalized)
        self.assertNotIn('-', normalized)