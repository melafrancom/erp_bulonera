# archivo: /var/www/miapp/afip/utils/excepciones.py

class ARCAException(Exception):
    """Excepción base para errores ARCA."""
    pass

class WSAAException(ARCAException):
    """Error en autenticación WSAA."""
    pass

class WSFEException(ARCAException):
    """Error en facturación WSFEV1."""
    pass

class CertificadoInvalidoException(ARCAException):
    """Certificado digital inválido o expirado."""
    pass

class ComprobanteDuplicadoException(ARCAException):
    """Intento de crear comprobante con número duplicado."""
    pass

class ComprobantePendienteException(ARCAException):
    """No se puede emitir, ya está en ARCA."""
    pass

class ConfiguracionARCAFaltanteException(ARCAException):
    """Falta configuración de ARCA para empresa."""
    pass