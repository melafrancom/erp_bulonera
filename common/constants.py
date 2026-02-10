"""
Constantes globales del sistema ERP/CRM.
Eventos de auditoría, estados, y configuración.
"""

class AuditEvent:
    """Tipos de eventos para el log de auditoría (solo críticos de negocio)"""
    # Facturación
    FACTURA_CREATED = "factura.created"
    FACTURA_UPDATED = "factura.updated"
    FACTURA_CANCELLED = "factura.cancelled"
    FACTURA_SENT_AFIP = "factura.sent_afip"
    
    # Pagos
    PAGO_REGISTERED = "pago.registered"
    PAGO_CANCELLED = "pago.cancelled"
    
    # Stock
    STOCK_ADJUSTED = "stock.adjusted"
    STOCK_LOW_ALERT = "stock.low_alert"
    
    # Precios
    PRECIO_UPDATED = "precio.updated"
    PRECIO_BULK_UPDATE = "precio.bulk_update"

    # Clientes
    CLIENTE_CREATED = "cliente.created"
    CLIENTE_UPDATED = "cliente.updated"
    CLIENTE_DELETED = "cliente.deleted"


class EntityStatus:
    """Estados genéricos para entidades"""
    DRAFT = "draft"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    
    CHOICES = [
        (DRAFT, "Borrador"),
        (ACTIVE, "Activo"),
        (CANCELLED, "Cancelado"),
        (ARCHIVED, "Archivado"),
    ]


class PaymentStatus:
    """Estados de pago"""
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    
    CHOICES = [
        (PENDING, "Pendiente"),
        (PARTIAL, "Pago Parcial"),
        (PAID, "Pagado"),
        (OVERDUE, "Vencido"),
    ]


class DocumentType:
    """Tipos de documento fiscal (Argentina)"""
    DNI = "DNI"
    CUIT = "CUIT"
    CUIL = "CUIL"
    PASSPORT = "PASAPORTE"
    
    CHOICES = [
        (DNI, "DNI"),
        (CUIT, "CUIT"),
        (CUIL, "CUIL"),
        (PASSPORT, "Pasaporte"),
    ]


class IVACondition:
    """Condiciones de IVA (Argentina)"""
    RESPONSABLE_INSCRIPTO = "RI"
    MONOTRIBUTO = "MO"
    EXENTO = "EX"
    CONSUMIDOR_FINAL = "CF"
    
    CHOICES = [
        (RESPONSABLE_INSCRIPTO, "Responsable Inscripto"),
        (MONOTRIBUTO, "Monotributista"),
        (EXENTO, "Exento"),
        (CONSUMIDOR_FINAL, "Consumidor Final"),
    ]

