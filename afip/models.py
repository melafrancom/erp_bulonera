# archivo: /var/www/miapp/afip/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from enum import IntEnum
import json

# ============================================================================
# TIPOS Y CONSTANTES
# ============================================================================

class TipoComprob(IntEnum):
    """Tipos de comprobante según ARCA/AFIP."""
    FACTURA_A = 1
    NOTA_DEBITO_A = 2
    NOTA_CREDITO_A = 3
    FACTURA_B = 6
    NOTA_DEBITO_B = 7
    NOTA_CREDITO_B = 8
    
    @classmethod
    def choices(cls):
        return [(e.value, e.name.replace('_', ' ')) for e in cls]

class TipoDocumento(IntEnum):
    """Tipo de documento del cliente."""
    DNI = 80
    CUIT = 86
    CUIL = 87
    
    @classmethod
    def choices(cls):
        return [(e.value, e.name) for e in cls]

# ============================================================================
# TOKENS Y AUTENTICACIÓN
# ============================================================================

class WSAAToken(models.Model):
    """Token de acceso a WSAA."""
    
    SERVICIO_CHOICES = [
        ('wsfe', 'Facturación Electrónica v1'),
        ('wsfe_v2', 'Facturación Electrónica v2'),
    ]
    
    AMBIENTE_CHOICES = [
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
    ]
    
    cuit = models.CharField(max_length=15, db_index=True)
    servicio = models.CharField(max_length=20, choices=SERVICIO_CHOICES)
    ambiente = models.CharField(max_length=20, choices=AMBIENTE_CHOICES)
    
    token = models.TextField()
    sign = models.TextField()
    
    generado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(db_index=True)
    
    class Meta:
        unique_together = ('cuit', 'servicio', 'ambiente')
        verbose_name = "Token WSAA"
        verbose_name_plural = "Tokens WSAA"
        indexes = [
            models.Index(fields=['cuit', 'servicio', 'ambiente']),
        ]
    
    def __str__(self):
        return f"Token {self.cuit} {self.servicio}"
    
    def esta_vigente(self):
        """Retorna True si el token aún no expiró (con margen de 5 minutos)."""
        return timezone.now() < (self.expira_en - timezone.timedelta(minutes=5))

    def tiempo_restante(self):
        """Retorna los segundos restantes de vida del token. Puede ser negativo si expiró."""
        delta = self.expira_en - timezone.now()
        return delta.total_seconds()

    @classmethod
    def obtener_token_vigente(cls, cuit, servicio, ambiente):
        """
        Busca y retorna un token vigente para la combinación dada.
        Retorna None si no existe o expiró.
        """
        try:
            token_obj = cls.objects.get(
                cuit=cuit,
                servicio=servicio,
                ambiente=ambiente
            )
            if token_obj.esta_vigente():
                return token_obj
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def obtener_o_generar(cls, cuit, servicio, ambiente, client):
        """Obtiene token vigente o genera uno nuevo."""
        # Intenta obtener del cache
        try:
            token_obj = cls.objects.get(
                cuit=cuit,
                servicio=servicio,
                ambiente=ambiente
            )
            if token_obj.esta_vigente():
                return token_obj
        except cls.DoesNotExist:
            pass
        
        # Genera uno nuevo
        resultado = client.obtener_ticket_acceso(servicio)
        if not resultado['success']:
            raise Exception(f"Error WSAA: {resultado['error']}")
        
        token_obj = cls.objects.create(
            cuit=cuit,
            servicio=servicio,
            ambiente=ambiente,
            token=resultado['token'],
            sign=resultado['sign'],
            expira_en=resultado['expiration']
        )
        
        return token_obj
    @classmethod
    def guardar_token(cls, cuit, servicio, ambiente, token, sign, expira_en):
        """
        Guarda o actualiza token.
        """
        obj, created = cls.objects.update_or_create(
            cuit=cuit,
            servicio=servicio,
            ambiente=ambiente,
            defaults={
                'token': token,
                'sign': sign,
                'expira_en': expira_en
            }
        )
        return obj

# ============================================================================
# CONFIGURACIÓN Y PARÁMETROS
# ============================================================================

class ConfiguracionARCA(models.Model):
    """Configuración de conexión a ARCA por empresa."""
    
    AMBIENTE_CHOICES = [
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
    ]
    
    empresa_cuit = models.CharField(max_length=15, unique=True, primary_key=True)
    ambiente = models.CharField(max_length=20, choices=AMBIENTE_CHOICES, default='homologacion')
    
    # Certificados
    ruta_certificado = models.CharField(
        max_length=500,
        help_text="Ruta absoluta a archivo .pem con certificado + clave privada"
    )
    password_certificado = models.CharField(
        max_length=255,
        blank=True,
        help_text="Contraseña del certificado si está protegido"
    )
    
    # Datos empresa
    razon_social = models.CharField(max_length=255)
    email_contacto = models.EmailField()
    
    # Punto de venta
    punto_venta = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    
    # Flags
    activo = models.BooleanField(default=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración ARCA"
        verbose_name_plural = "Configuraciones ARCA"
    
    def __str__(self):
        return f"{self.razon_social} ({self.ambiente})"

# ============================================================================
# COMPROBANTES Y FACTURACIÓN
# ============================================================================

class Comprobante(models.Model):
    """
    Comprobante (Factura/Nota de Crédito/etc).
    
    Estados:
    - BORRADOR: Sin emitir
    - PENDIENTE: Esperando respuesta ARCA
    - AUTORIZADO: CAE obtenido
    - RECHAZADO: Error ARCA
    """
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE', 'Pendiente (enviado a ARCA)'),
        ('AUTORIZADO', 'Autorizado (CAE obtenido)'),
        ('RECHAZADO', 'Rechazado'),
    ]
    
    empresa_cuit = models.ForeignKey(
        ConfiguracionARCA,
        on_delete=models.PROTECT,
        to_field='empresa_cuit'
    )
    
    # Referencia a la venta origen (para trazabilidad)
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comprobantes_arca',
        help_text='Venta que originó este comprobante'
    )
    
    # Identificación
    tipo_compr = models.IntegerField(
        choices=TipoComprob.choices(),
        help_text="Tipo de comprobante (Factura A, B, etc.)"
    )
    punto_venta = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    numero = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    
    # Fechas
    fecha_compr = models.DateField(
        help_text="Fecha del comprobante"
    )
    fecha_vto_pago = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha vencimiento pago"
    )
    
    # Cliente
    doc_cliente_tipo = models.IntegerField(
        choices=TipoDocumento.choices()
    )
    doc_cliente = models.CharField(
        max_length=20,
        help_text="CUIT/CUIL/DNI del cliente"
    )
    razon_social_cliente = models.CharField(max_length=255)
    
    # Montos
    monto_neto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # ARCA
    cae = models.CharField(
        max_length=14,
        blank=True,
        help_text="Código de Autorización Electrónica"
    )
    fecha_vto_cae = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento del CAE"
    )
    
    # Control
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='BORRADOR'
    )
    
    respuesta_arca_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Respuesta completa de ARCA"
    )
    
    error_msg = models.TextField(
        blank=True,
        help_text="Mensaje de error si ARCA rechazó"
    )
    
    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    usuario_creacion = models.CharField(
        max_length=255,
        blank=True,
        help_text="Usuario que creó el comprobante"
    )
    
    class Meta:
        unique_together = ('empresa_cuit', 'tipo_compr', 'punto_venta', 'numero')
        indexes = [
            models.Index(fields=['empresa_cuit', 'estado']),
            models.Index(fields=['fecha_compr']),
            models.Index(fields=['doc_cliente']),
        ]
        verbose_name = "Comprobante ARCA"
        verbose_name_plural = "Comprobantes ARCA"
    
    def __str__(self):
        tipo = dict(TipoComprob.choices()).get(self.tipo_compr, 'Desc')
        return f"{tipo} {self.punto_venta:04d}-{self.numero:08d}"
    
    @property
    def numero_completo(self):
        return f"{self.punto_venta:04d}-{self.numero:08d}"
    
    def puede_emitirse(self):
        """¿El comprobante está listo para emitir?"""
        return self.estado == 'BORRADOR' and self.monto_total > 0
    
    def marcar_como_enviado(self):
        """Marca como pendiente (ya se envió a ARCA)."""
        self.estado = 'PENDIENTE'
        self.save()
    
    def marcar_como_autorizado(self, cae, fecha_vto_cae, respuesta_json):
        """Marca como autorizado."""
        self.estado = 'AUTORIZADO'
        self.cae = cae
        self.fecha_vto_cae = fecha_vto_cae
        self.respuesta_arca_json = respuesta_json
        self.error_msg = ''
        self.save()
    
    def marcar_como_rechazado(self, error_msg, respuesta_json):
        """Marca como rechazado."""
        self.estado = 'RECHAZADO'
        self.error_msg = error_msg
        self.respuesta_arca_json = respuesta_json
        self.save()

# ============================================================================
# DETALLES DE COMPROBANTES
# ============================================================================

class ComprobRenglon(models.Model):
    """Línea de detalle de un comprobante."""
    
    comprobante = models.ForeignKey(
        Comprobante,
        on_delete=models.CASCADE,
        related_name='renglones'
    )
    
    numero_linea = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    
    descripcion = models.CharField(max_length=500)
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    
    alicuota_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        default=21
    )
    
    class Meta:
        unique_together = ('comprobante', 'numero_linea')
    
    def __str__(self):
        return f"Línea {self.numero_linea}: {self.descripcion[:50]}"
    
    def calcular_iva(self):
        """Calcula IVA para esta línea."""
        return (self.subtotal * self.alicuota_iva / 100).quantize(
            Decimal('0.01')
        )

# ============================================================================
# LOGS Y AUDITORÍA
# ============================================================================

class LogARCA(models.Model):
    """Log de todas las transacciones con ARCA."""
    
    TIPO_CHOICES = [
        ('WSAA_LOGIN', 'Login WSAA'),
        ('WSAA_ERROR', 'Error WSAA'),
        ('FE_AUTORIZAR', 'Autorizar comprobante'),
        ('FE_ERROR', 'Error FE'),
        ('FE_CONSULTAR', 'Consultar CAE'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    cuit = models.CharField(max_length=15)
    servicio = models.CharField(max_length=50)
    
    # Request
    request_xml = models.TextField(blank=True)
    
    # Response
    response_xml = models.TextField(blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    
    # Errores
    error = models.TextField(blank=True)
    
    # Comprobante relacionado
    comprobante = models.ForeignKey(
        Comprobante,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['cuit', 'timestamp']),
            models.Index(fields=['tipo']),
        ]
        verbose_name = "Log ARCA"
        verbose_name_plural = "Logs ARCA"
    
    def __str__(self):
        return f"{self.tipo} - {self.timestamp}"