# sales/web/views/web_views.py
"""
Vistas web del módulo Sales — Django Templates (PWA).

Arquitectura:
    - Las vistas son coordinadoras HTTP (thin views).
    - Toda la lógica de negocio vive en sales/services.py.
    - Los formularios interactúan con la API REST vía JS.
    - Las acciones POST (confirmar, cancelar, mover estado) llaman a services directamente.

Vistas disponibles:
    DASHBOARD
        sales_dashboard         → Métricas generales

    PRESUPUESTOS (QUOTES)
        quote_list              → Listado con filtros
        quote_detail            → Detalle + acciones
        quote_create            → Formulario creación
        quote_update            → Formulario edición

    VENTAS (SALES)
        sale_list               → Listado con filtros
        sale_detail             → Detalle + acciones + items
        sale_create             → Formulario creación directa (mostrador)

    ACCIONES DE VENTA (POST only)
        sale_confirm            → Confirma una venta draft
        sale_cancel             → Cancela una venta
        sale_move_status        → Avanza estado del proceso
        sale_convert_from_quote → Convierte presupuesto en venta
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings

from sales.models import Quote, QuoteItem, Sale, SaleItem
from sales.services import cancel_sale, confirm_sale, convert_quote_to_sale, move_sale_status

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE AUTORIZACIÓN (thin wrappers sobre el User model)
# ─────────────────────────────────────────────────────────────────────────────

def _is_privileged(user):
    """Superuser, admin o manager: puede ver y operar sobre todo."""
    return (
        user.is_superuser
        or getattr(user, 'role', '') in ('admin', 'manager')
    )


def _can_manage_sales(user):
    """Puede crear/editar ventas."""
    return _is_privileged(user) or getattr(user, 'can_manage_sales', False)


def _can_manage_quotes(user):
    """Puede crear/editar presupuestos."""
    return _is_privileged(user) or getattr(user, 'can_manage_sales', False)


def _owns_or_privileged(user, obj):
    """El usuario es el creador del objeto o tiene rol privilegiado."""
    return _is_privileged(user) or getattr(obj, 'created_by_id', None) == user.pk


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def sales_dashboard(request):
    """Dashboard principal de ventas con métricas clave."""

    # ── Presupuestos ──────────────────────────────────────────────────────────
    quotes_qs = Quote.objects.all()
    total_quotes    = quotes_qs.count()
    quotes_sent     = quotes_qs.filter(status='sent').count()
    quotes_accepted = quotes_qs.filter(status='accepted').count()
    quotes_draft    = quotes_qs.filter(status='draft').count()
    quotes_pending  = quotes_qs.filter(status__in=['draft', 'sent']).count()
    recent_quotes   = quotes_qs.select_related('customer').order_by('-date')[:5]

    # ── Ventas ────────────────────────────────────────────────────────────────
    sales_qs = Sale.objects.all()
    total_sales           = sales_qs.count()
    sales_confirmed       = sales_qs.filter(status='confirmed').count()
    sales_delivered       = sales_qs.filter(status='delivered').count()
    sales_unpaid          = sales_qs.filter(payment_status='unpaid').count()
    sales_partially_paid  = sales_qs.filter(payment_status='partially_paid').count()
    sales_paid            = sales_qs.filter(payment_status='paid').count()
    sales_pending_payment = sales_qs.exclude(payment_status='paid').count()
    recent_sales          = sales_qs.select_related('customer').order_by('-date')[:5]

    context = {
        # Quotes
        'total_quotes':     total_quotes,
        'quotes_sent':      quotes_sent,
        'quotes_accepted':  quotes_accepted,
        'quotes_draft':     quotes_draft,
        'quotes_pending':   quotes_pending,
        'recent_quotes':    recent_quotes,
        # Sales
        'total_sales':            total_sales,
        'sales_confirmed':        sales_confirmed,
        'sales_delivered':        sales_delivered,
        'sales_unpaid':           sales_unpaid,
        'sales_partially_paid':   sales_partially_paid,
        'sales_paid':             sales_paid,
        'sales_pending_payment':  sales_pending_payment,
        'recent_sales':           recent_sales,
    }

    return render(request, 'sales/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PRESUPUESTOS — LISTADO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def quote_list(request):
    """
    Listado de presupuestos con filtros por estado y búsqueda de texto.

    Los operators solo ven sus propios presupuestos.
    Managers/admins ven todos.
    """
    quotes = Quote.objects.select_related('customer', 'created_by').order_by('-date')

    # Acotar queryset según rol
    if not _is_privileged(request.user):
        quotes = quotes.filter(created_by=request.user)

    # Totales globales (sobre queryset ya acotado, antes de filtros adicionales)
    total_quotes    = quotes.count()
    quotes_sent     = quotes.filter(status='sent').count()
    quotes_accepted = quotes.filter(status='accepted').count()

    # ── Filtros ───────────────────────────────────────────────────────────────
    status_filter = request.GET.get('status', '').strip()
    search        = request.GET.get('search', '').strip()

    if status_filter:
        quotes = quotes.filter(status=status_filter)

    if search:
        quotes = quotes.filter(
            models.Q(number__icontains=search)
            | models.Q(customer__business_name__icontains=search)
            | models.Q(items__product__code__icontains=search)
            | models.Q(items__product__sku__icontains=search)
            | models.Q(items__product__other_codes__icontains=search)
        ).distinct()

    # ── Paginación ────────────────────────────────────────────────────────────
    paginator = Paginator(quotes, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))

    context = {
        'quotes':           page_obj,
        'total_quotes':     total_quotes,
        'quotes_sent':      quotes_sent,
        'quotes_accepted':  quotes_accepted,
        'status_filter':    status_filter,
        'search':           search,
    }

    return render(request, 'sales/quote_list.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PRESUPUESTOS — DETALLE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def quote_detail(request, pk):
    """
    Detalle de un presupuesto con sus ítems y acciones disponibles.

    Las acciones del flujo (send, accept, reject, convert) se ejecutan
    vía la API REST desde el template JS. Esta vista solo renderiza el estado.
    """
    quote = get_object_or_404(
        Quote.objects.select_related('customer', 'created_by')
                     .prefetch_related('items__product'),
        pk=pk,
    )

    # Control de acceso: operators solo ven los suyos
    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    # ── Acciones disponibles según estado ─────────────────────────────────────
    can_edit    = quote.is_editable()
    can_send    = quote.status == 'draft'
    can_accept  = quote.status == 'sent'
    can_reject  = quote.status in ('sent', 'draft')
    can_convert = quote.can_be_converted()
    can_delete  = quote.status == 'draft' and _can_manage_quotes(request.user)

    # Venta generada (si fue convertido)
    converted_sale = None
    if quote.status == 'converted':
        try:
            converted_sale = quote.converted_sale  # OneToOne reverse
        except Sale.DoesNotExist:
            pass

    context = {
        'quote':            quote,
        'items':            quote.items.select_related('product').order_by('line_order'),
        'can_edit':         can_edit,
        'can_send':         can_send,
        'can_accept':       can_accept,
        'can_reject':       can_reject,
        'can_convert':      can_convert,
        'can_delete':       can_delete,
        'converted_sale':   converted_sale,
    }

    return render(request, 'sales/quote_detail.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PRESUPUESTOS — CREAR / EDITAR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def quote_create(request):
    """
    Formulario para crear un nuevo presupuesto.

    El template usa Alpine.js + fetch() para interactuar con la API REST.
    Esta vista solo renderiza el formulario vacío con los datos maestros
    (clientes, productos) necesarios para los selects.
    """
    if not _can_manage_quotes(request.user):  # ← no lo elimines
        messages.error(request, 'No tenés permisos para crear presupuestos.')
        return redirect('sales_web:quote_list')

    context = {
        'products':      _get_products_queryset(),
        'pricelists':    _get_pricelists_queryset(),
        'categories':    _get_categories_queryset(),
        'subcategories': _get_subcategories_queryset(),
        'today':         timezone.now().date(),
        'mode':          'create',
    }
    return render(request, 'sales/quote_form.html', context)


@login_required
def quote_update(request, pk):
    """
    Formulario para editar un presupuesto existente.

    Solo se pueden editar presupuestos en estado 'draft' o 'sent'.
    La edición real se realiza via API REST desde el JS del template.
    """
    quote = get_object_or_404(Quote, pk=pk)

    # Acceso
    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    if not quote.is_editable():
        messages.warning(
            request,
            f'El presupuesto {quote.number} no puede editarse '
            f'(estado: {quote.get_status_display()}).'
        )
        return redirect('sales_web:quote_detail', pk=quote.pk)

    if not _can_manage_quotes(request.user):
        messages.error(request, 'No tenés permisos para editar presupuestos.')
        return redirect('sales_web:quote_detail', pk=quote.pk)

    customers = _get_customers_queryset()
    products  = _get_products_queryset()

    context = {
        'quote':      quote,
        'items':      quote.items.select_related('product').order_by('line_order'),
        'customers':  customers,
        'products':      products,
        'pricelists':    _get_pricelists_queryset(),
        'categories':    _get_categories_queryset(),
        'subcategories': _get_subcategories_queryset(),
        'mode':          'update',
    }

    return render(request, 'sales/quote_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# VENTAS — LISTADO
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def sale_list(request):
    """
    Listado de ventas con filtros por estado comercial, pago y búsqueda.

    Operators: solo sus propias ventas.
    Managers/admins: todas las ventas.
    """
    sales = Sale.objects.select_related('customer', 'created_by').order_by('-date')

    if not _is_privileged(request.user):
        sales = sales.filter(created_by=request.user)

    # Totales (sobre queryset acotado, antes de filtros adicionales)
    total_sales          = sales.count()
    sales_confirmed      = sales.filter(status='confirmed').count()
    sales_delivered      = sales.filter(status='delivered').count()
    sales_unpaid         = sales.filter(payment_status='unpaid').count()
    sales_partially_paid = sales.filter(payment_status='partially_paid').count()
    sales_paid           = sales.filter(payment_status='paid').count()

    # ── Filtros ───────────────────────────────────────────────────────────────
    status_filter  = request.GET.get('status', '').strip()
    payment_filter = request.GET.get('payment_status', '').strip()
    search         = request.GET.get('search', '').strip()

    if status_filter:
        sales = sales.filter(status=status_filter)

    if payment_filter:
        sales = sales.filter(payment_status=payment_filter)

    if search:
        sales = sales.filter(
            models.Q(number__icontains=search)
            | models.Q(customer__business_name__icontains=search)
            | models.Q(items__product__code__icontains=search)
            | models.Q(items__product__sku__icontains=search)
            | models.Q(items__product__other_codes__icontains=search)
        ).distinct()

    # ── Paginación ────────────────────────────────────────────────────────────
    paginator = Paginator(sales, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))

    context = {
        'sales':                 page_obj,
        'total_sales':           total_sales,
        'sales_confirmed':       sales_confirmed,
        'sales_delivered':       sales_delivered,
        'sales_unpaid':          sales_unpaid,
        'sales_partially_paid':  sales_partially_paid,
        'sales_paid':            sales_paid,
        'status_filter':         status_filter,
        'payment_status_filter': payment_filter,
        'search':                search,
    }

    return render(request, 'sales/sale_list.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# VENTAS — DETALLE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def sale_detail(request, pk):
    """
    Detalle completo de una venta: ítems, totales, estados y acciones disponibles.

    Las acciones pesadas (confirmar, cancelar, avanzar estado) se realizan
    mediante views POST dedicadas (sale_confirm, sale_cancel, sale_move_status).
    """
    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'created_by', 'quote')
                    .prefetch_related('items__product'),
        pk=pk,
    )

    # Control de acceso
    if not _owns_or_privileged(request.user, sale):
        messages.error(request, 'No tenés acceso a esta venta.')
        return redirect('sales_web:sale_list')

    # ── Acciones disponibles ──────────────────────────────────────────────────
    can_confirm = sale.status == 'draft' and _can_manage_sales(request.user)
    can_edit    = sale.is_editable() and _can_manage_sales(request.user)
    can_invoice = sale.can_be_invoiced() and _is_privileged(request.user)

    # Cancelar: managers/admins pueden cancelar cualquier estado no terminal.
    # Operators solo pueden cancelar sus propios drafts.
    can_cancel = (
        sale.status not in ('delivered', 'cancelled')
        and (
            _is_privileged(request.user)
            or (sale.status == 'draft' and sale.created_by == request.user)
        )
    )

    # Avanzar estado del proceso (confirmed → in_preparation → ready → delivered)
    can_advance = (
        sale.status in ('confirmed', 'in_preparation', 'ready')
        and _can_manage_sales(request.user)
    )

    # Próximo estado y etiqueta para el botón de avance
    status_flow = {
        'confirmed':      ('in_preparation', 'Poner en Preparación'),
        'in_preparation': ('ready',          'Marcar Lista para Entregar'),
        'ready':          ('delivered',      'Marcar como Entregada'),
    }
    next_status, next_status_label = status_flow.get(sale.status, (None, None))

    # Venta origen (si vino de un presupuesto)
    source_quote = None
    if sale.quote_id:
        try:
            source_quote = sale.quote
        except Quote.DoesNotExist:
            pass
    
    invoice = sale.facturas.filter(tipo_comprobante__in=[1, 6, 81, 82, 83]).first()
    nota_credito = sale.facturas.filter(tipo_comprobante__in=[3, 8, 85, 86, 87]).first()
    
    # Datos para el modal de tickets fiscales
    from bills.services import get_next_ticket_number
    from afip.models import ConfiguracionARCA

    ticket_config = None
    try:
        config = ConfiguracionARCA.objects.filter(activo=True).first()
        if config:
            ticket_config = {
                'punto_venta': config.punto_venta,
                'next_ticket_a':  get_next_ticket_number(config.punto_venta, 81),
                'next_ticket_b':  get_next_ticket_number(config.punto_venta, 82),
                'next_ticket_cf': get_next_ticket_number(config.punto_venta, 83),
            }
    except Exception:
        pass  # Si no hay config ARCA, el modal pedirá el número sin sugerencia

    context = {
        'sale':              sale,
        'items':             sale.items.select_related('product').order_by('id'),
        'source_quote':      source_quote,
        'can_confirm':       can_confirm,
        'can_edit':          can_edit,
        'can_cancel':        can_cancel,
        'can_advance':       can_advance,
        'can_invoice':       can_invoice,
        'next_status':       next_status,
        'next_status_label': next_status_label,
        'invoice':           invoice,
        'nota_credito':      nota_credito,
        'ticket_config':     ticket_config,
        'tipos_ticket': [
            {'value': 81, 'label': 'Tique Factura A'},
            {'value': 82, 'label': 'Tique Factura B'},
            {'value': 83, 'label': 'Tique a Consumidor Final'},
        ],
    }

    return render(request, 'sales/sale_detail.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# VENTAS — CREAR (Venta directa / Mostrador)
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def sale_create(request):
    """
    Formulario para crear una venta directa (venta de mostrador, B2C).

    El template usa Alpine.js + fetch() hacia /api/sales/sales/ para
    enviar los datos. Esta vista solo renderiza el formulario con maestros.
    """
    if not _can_manage_quotes(request.user):  # ← no lo elimines
        messages.error(request, 'No tenés permisos para crear presupuestos.')
        return redirect('sales_web:quote_list')

    context = {
        'products':      _get_products_queryset(),
        'pricelists':    _get_pricelists_queryset(),
        'categories':    _get_categories_queryset(),
        'subcategories': _get_subcategories_queryset(),
        'today':         timezone.now().date(),
        'mode':          'create',
    }
    return render(request, 'sales/sale_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# ACCIONES DE VENTA — POST only
# Nota: estas vistas son "server actions" que llaman al service layer.
# Devuelven redirect con mensaje Django, NO JSON (para flujo HTML clásico).
# Si la acción se triggerea desde JS, usar los endpoints REST de la API.
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def sale_confirm(request, pk):
    """
    Confirma una venta en estado draft.

    POST /sales/sales/<pk>/confirm/

    Permisos requeridos: can_manage_sales (o rol privilegiado).
    Efectos: llama a confirm_sale() → cambia status, dispara signals.
    """
    sale = get_object_or_404(Sale, pk=pk)

    if not _can_manage_sales(request.user):
        messages.error(request, 'No tenés permisos para confirmar ventas.')
        return redirect('sales_web:sale_detail', pk=pk)

    if not _owns_or_privileged(request.user, sale):
        messages.error(request, 'No tenés acceso a esta venta.')
        return redirect('sales_web:sale_list')

    if sale.status != 'draft':
        messages.warning(
            request,
            f'La venta {sale.number} ya está en estado '
            f'"{sale.get_status_display()}" y no puede confirmarse.'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    try:
        confirm_sale(sale=sale, user=request.user)
        messages.success(request, f'✅ Venta {sale.number} confirmada exitosamente.')
        logger.info('Sale %s confirmed by user %s', sale.number, request.user.username)

    except ValueError as exc:
        messages.error(request, f'❌ No se pudo confirmar: {exc}')
        logger.warning(
            'Failed to confirm sale %s by user %s: %s',
            sale.number, request.user.username, exc,
        )
    except Exception:
        logger.exception('Unexpected error confirming sale %s', pk)
        messages.error(request, 'Ocurrió un error inesperado. Intentá de nuevo.')

    return redirect('sales_web:sale_detail', pk=pk)


@login_required
@require_POST
def sale_cancel(request, pk):
    """
    Cancela una venta.

    POST /sales/sales/<pk>/cancel/
    Body (form): reason (str, opcional)

    Regla: Operators solo pueden cancelar sus propios drafts.
           Managers/admins pueden cancelar cualquier estado no terminal.
    """
    sale = get_object_or_404(Sale, pk=pk)

    if not _owns_or_privileged(request.user, sale):
        messages.error(request, 'No tenés acceso a esta venta.')
        return redirect('sales_web:sale_list')

    if sale.status in ('delivered', 'cancelled'):
        messages.warning(
            request,
            f'La venta {sale.number} no puede cancelarse '
            f'(estado: {sale.get_status_display()}).'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    # Operators no privilegiados solo pueden cancelar sus propios drafts
    if not _is_privileged(request.user) and sale.status != 'draft':
        messages.error(
            request,
            'Solo managers o administradores pueden cancelar ventas que ya fueron confirmadas.'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    reason = request.POST.get('reason', '').strip() or 'Sin motivo especificado'

    try:
        cancel_sale(sale=sale, user=request.user, reason=reason)
        messages.success(request, f'Venta {sale.number} cancelada correctamente.')
        logger.info(
            'Sale %s cancelled by user %s. Reason: %s',
            sale.number, request.user.username, reason,
        )

    except ValueError as exc:
        messages.error(request, f'No se pudo cancelar la venta: {exc}')
        logger.warning(
            'Failed to cancel sale %s by user %s: %s',
            sale.number, request.user.username, exc,
        )
    except Exception:
        logger.exception('Unexpected error cancelling sale %s', pk)
        messages.error(request, 'Ocurrió un error inesperado. Intentá de nuevo.')

    return redirect('sales_web:sale_detail', pk=pk)


@login_required
@require_POST
def sale_move_status(request, pk):
    """
    Avanza el estado del proceso de una venta confirmada.

    POST /sales/sales/<pk>/move_status/
    Body (form):
        new_status      (str)  — in_preparation | ready | delivered
        delivery_notes  (str)  — nota opcional al marcar como entregada

    Máquina de estados permitida desde esta view:
        confirmed → in_preparation
        in_preparation → ready
        ready → delivered

    Para cancelar usar sale_cancel. Para confirmar usar sale_confirm.
    """
    sale = get_object_or_404(Sale, pk=pk)

    if not _can_manage_sales(request.user):
        messages.error(request, 'No tenés permisos para cambiar el estado de ventas.')
        return redirect('sales_web:sale_detail', pk=pk)

    if not _owns_or_privileged(request.user, sale):
        messages.error(request, 'No tenés acceso a esta venta.')
        return redirect('sales_web:sale_list')

    new_status = request.POST.get('new_status', '').strip()
    delivery_notes = request.POST.get('delivery_notes', '').strip()

    try:
        move_sale_status(
            sale=sale,
            user=request.user,
            new_status=new_status,
            delivery_notes=delivery_notes
        )
        messages.success(
            request,
            f'Venta {sale.number} movida a "{sale.get_status_display()}".'
        )
        logger.info(
            'Sale %s moved to %s by user %s',
            sale.number, new_status, request.user.username,
        )

    except ValueError as exc:
        messages.error(request, f'No se pudo mover el estado: {exc}')
    except Exception:
        logger.exception('Unexpected error moving status of sale %s', pk)
        messages.error(request, 'Ocurrió un error inesperado. Intentá de nuevo.')

    return redirect('sales_web:sale_detail', pk=pk)




@login_required
@require_POST
def sale_convert_from_quote(request, quote_pk):
    """
    Convierte un presupuesto aceptado en una venta draft.

    POST /sales/quotes/<quote_pk>/convert/
    Body (form): sin campos obligatorios. Las modificaciones de precio
                 se manejan vía la API REST (/api/sales/quotes/<id>/convert/).

    Esta view es el punto de entrada desde el template de quote_detail
    para una conversión sin modificaciones.
    """
    quote = get_object_or_404(Quote, pk=quote_pk)

    if not _can_manage_sales(request.user):
        messages.error(request, 'No tenés permisos para convertir presupuestos en ventas.')
        return redirect('sales_web:quote_detail', pk=quote_pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    if not quote.can_be_converted():
        messages.warning(
            request,
            f'El presupuesto {quote.number} no puede convertirse '
            f'(estado: {quote.get_status_display()}, '
            f'válido hasta: {quote.valid_until}).'
        )
        return redirect('sales_web:quote_detail', pk=quote_pk)

    try:
        sale = convert_quote_to_sale(quote=quote, user=request.user)
        messages.success(
            request,
            f'✅ Presupuesto {quote.number} convertido. '
            f'Se creó la venta {sale.number}.'
        )
        logger.info(
            'Quote %s converted to sale %s by user %s',
            quote.number, sale.number, request.user.username,
        )
        return redirect('sales_web:sale_detail', pk=sale.pk)

    except ValueError as exc:
        messages.error(request, f'No se pudo convertir el presupuesto: {exc}')
        logger.warning(
            'Failed to convert quote %s by user %s: %s',
            quote.number, request.user.username, exc,
        )
    except Exception:
        logger.exception('Unexpected error converting quote %s', quote_pk)
        messages.error(request, 'Ocurrió un error inesperado. Intentá de nuevo.')

    return redirect('sales_web:quote_detail', pk=quote_pk)


# ─────────────────────────────────────────────────────────────────────────────
# ACCIONES DE PRESUPUESTO — POST only
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def quote_send(request, pk):
    """
    Marca un presupuesto como enviado al cliente.

    POST /ventas/presupuestos/<pk>/enviar/
    """
    quote = get_object_or_404(Quote, pk=pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    if quote.status not in ('draft', 'sent'):
        messages.warning(
            request,
            f'El presupuesto {quote.number} no puede enviarse '
            f'(estado: {quote.get_status_display()}).'
        )
        return redirect('sales_web:quote_detail', pk=pk)

    quote.status = 'sent'
    quote.save(update_fields=['status'])
    
    try:
        from sales.tasks import send_quote_email_task
        send_quote_email_task.delay(quote.id)
        messages.success(request, f'✅ Presupuesto {quote.number} marcado como enviado y encolado para email.')
    except Exception:
        logger.exception("Error al encolar tarea de envío de email para presupuesto %s", quote.pk)
        messages.warning(
            request, 
            f'⚠️ Presupuesto {quote.number} marcado como enviado, pero falló el envío automático por email.'
        )

    logger.info('Quote %s sent by user %s', quote.number, request.user.username)
    return redirect('sales_web:quote_detail', pk=pk)


@login_required
@require_POST
def quote_send_email(request, pk):
    """
    POST /ventas/presupuestos/<pk>/enviar-email/
    """
    quote = get_object_or_404(Quote, pk=pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    recipient_email = request.POST.get('recipient_email', '').strip()
    if not recipient_email:
        messages.error(request, 'Debes proporcionar un email de destino.')
        return redirect('sales_web:quote_detail', pk=pk)
        
    if quote.status not in ('draft', 'sent', 'accepted'):
        messages.warning(
            request,
            f'El presupuesto {quote.number} no puede compartirse '
            f'(estado: {quote.get_status_display()}).'
        )
        return redirect('sales_web:quote_detail', pk=pk)

    # Actualizar estado si es draft
    if quote.status == 'draft':
        quote.status = 'sent'
        quote.save(update_fields=['status'])

    try:
        from sales.tasks import send_quote_email_task
        send_quote_email_task.delay(quote.id, recipient_email)
        messages.success(request, f'✅ Presupuesto {quote.number} encolado para enviar por email a {recipient_email}.')
    except Exception:
        logger.exception("Error al encolar tarea de envío de email para presupuesto %s", quote.pk)
        messages.error(request, 'Hubo un error al intentar enviar el correo. Por favor intentá de nuevo.')

    logger.info('Quote %s shared via email to %s by user %s', quote.number, recipient_email, request.user.username)
    return redirect('sales_web:quote_detail', pk=pk)


@login_required
@require_POST
def quote_accept(request, pk):
    """
    Marca un presupuesto como aceptado por el cliente.

    POST /ventas/presupuestos/<pk>/aceptar/
    """
    quote = get_object_or_404(Quote, pk=pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    if quote.status not in ('draft', 'sent'):
        messages.warning(
            request,
            f'Solo los presupuestos en borrador o enviados pueden aceptarse '
            f'(estado actual: {quote.get_status_display()}).'
        )
        return redirect('sales_web:quote_detail', pk=pk)

    quote.status = 'accepted'
    quote.save(update_fields=['status'])
    messages.success(request, f'✅ Presupuesto {quote.number} marcado como aceptado.')
    logger.info('Quote %s accepted by user %s', quote.number, request.user.username)
    return redirect('sales_web:quote_detail', pk=pk)


@login_required
@require_POST
def quote_reject(request, pk):
    """
    Marca un presupuesto como rechazado por el cliente.

    POST /ventas/presupuestos/<pk>/rechazar/

    Body (form): reason (str, opcional)
    """
    quote = get_object_or_404(Quote, pk=pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    if quote.status not in ('draft', 'sent'):
        messages.warning(
            request,
            f'Solo los presupuestos en borrador o enviados pueden rechazarse '
            f'(estado actual: {quote.get_status_display()}).'
        )
        return redirect('sales_web:quote_detail', pk=pk)

    reason = request.POST.get('reason', '').strip()
    quote.status = 'rejected'
    if reason:
        from django.utils import timezone as tz
        quote.internal_notes = (quote.internal_notes or '') + \
            f"\n\n[{tz.now().strftime('%Y-%m-%d %H:%M')}] Rechazado: {reason}"
        quote.save(update_fields=['status', 'internal_notes'])
    else:
        quote.save(update_fields=['status'])

    messages.success(request, f'Presupuesto {quote.number} marcado como rechazado.')
    logger.info('Quote %s rejected by user %s', quote.number, request.user.username)
    return redirect('sales_web:quote_detail', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS PARA DATOS MAESTROS
# Lazy imports: estas apps pueden no estar disponibles en todas las etapas
# de desarrollo. Fallan silenciosamente retornando QuerySet vacío.
# ─────────────────────────────────────────────────────────────────────────────

def _get_customers_queryset():
    """
    Retorna el queryset de clientes activos.
    Si la app 'customers' no está disponible, retorna lista vacía.
    """
    try:
        from customers.models import Customer
        return Customer.objects.filter(is_active=True).order_by('business_name')
    except Exception:
        logger.warning('customers app not available, returning empty queryset')
        return []


def _get_products_queryset():
    """
    Retorna el queryset de productos activos.
    Si la app 'products' no está disponible, retorna lista vacía.
    """
    try:
        from products.models import Product
        return Product.objects.filter(is_active=True).order_by('name')
    except Exception:
        logger.warning('products app not available, returning empty queryset')
        return []


def _get_pricelists_queryset():
    """
    Retorna las listas de precios activas.
    Cada <option> en el template usará data-type y data-percentage.
    """
    try:
        from products.models import PriceList
        return PriceList.objects.filter(is_active=True).order_by('priority', 'name')
    except Exception:
        logger.warning('PriceList not available, returning empty list')
        return []

def _get_categories_queryset():
    """Retorna las categorías activas."""
    try:
        from products.models import Category
        return Category.objects.filter(is_active=True).order_by('name')
    except Exception:
        return []

def _get_subcategories_queryset():
    """Retorna las subcategorías activas."""
    try:
        from products.models import Subcategory
        return Subcategory.objects.filter(is_active=True).order_by('name')
    except Exception:
        return []

@login_required
@require_POST
def sale_invoice(request, pk):
    """
    Emite factura para una venta.
    
    POST /sales/sales/<pk>/facturar/
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    if not _is_privileged(request.user):
        messages.error(request, 'No tenés permisos para facturar ventas.')
        return redirect('sales_web:sale_detail', pk=pk)

    if not sale.can_be_invoiced():
        messages.warning(
            request,
            f'La venta {sale.number} no se puede facturar en este momento. '
            f'Asegurate de que esté confirmada y tenga CUIT si es a responsable inscripto.'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    try:
        from bills.services import facturar_venta
        # facturar_venta maneja la creación de Invoice y Comprobante AFIP
        result = facturar_venta(sale=sale, user=request.user, async_emission=True)
        messages.success(request, f"✅ Venta {sale.number} enviada a facturar. ID: {result.get('invoice_id')}")
        logger.info('Sale %s invoiced by user %s', sale.number, request.user.username)
    except ValueError as exc:
        messages.error(request, f'❌ Error al facturar: {exc}')
        logger.warning('Failed to invoice sale %s by user %s: %s', sale.number, request.user.username, exc)
    except Exception as exc:
        logger.exception('Unexpected error invoicing sale %s', pk)
        messages.error(request, 'Ocurrió un error inesperado al intentar facturar.')

    return redirect('sales_web:sale_detail', pk=pk)

@login_required
@require_POST
def sale_register_ticket(request, pk):
    """
    Registra un ticket de controlador fiscal para una venta.

    POST /ventas/ventas/<pk>/registrar-ticket/

    Body (form):
        tipo_comprobante  (int): 81, 82 o 83
        punto_venta       (int): Número de punto de venta
        numero_ticket     (int): Número que imprimió la máquina

    Permisos: can_manage_sales o rol privilegiado.
    """
    from bills.models import Invoice
    sale = get_object_or_404(Sale, pk=pk)

    if not _can_manage_sales(request.user):
        messages.error(request, 'No tenés permisos para registrar tickets fiscales.')
        return redirect('sales_web:sale_detail', pk=pk)

    if not _owns_or_privileged(request.user, sale):
        messages.error(request, 'No tenés acceso a esta venta.')
        return redirect('sales_web:sale_list')

    # Parsear y validar inputs del formulario
    try:
        tipo_comprobante = int(request.POST.get('tipo_comprobante', 0))
        punto_venta      = int(request.POST.get('punto_venta', 0))
        numero_ticket    = int(request.POST.get('numero_ticket', 0))
    except (ValueError, TypeError):
        messages.error(request, 'Los datos del formulario son inválidos.')
        return redirect('sales_web:sale_detail', pk=pk)

    try:
        from bills.services import register_manual_ticket
        invoice = register_manual_ticket(
            sale=sale,
            user=request.user,
            punto_venta=punto_venta,
            numero_ticket=numero_ticket,
            tipo_comprobante=tipo_comprobante,
        )
        tipo_display = dict(Invoice.TIPO_COMPROBANTE_CHOICES).get(tipo_comprobante, str(tipo_comprobante))
        messages.success(
            request,
            f'✅ {tipo_display} N° {invoice.number} registrado correctamente para {sale.number}.'
        )
        logger.info(
            'Ticket manual %s registered for sale %s by user %s',
            invoice.number, sale.number, request.user.username,
        )
    except ValueError as exc:
        messages.error(request, f'❌ {exc}')
        logger.warning(
            'Failed to register ticket for sale %s by user %s: %s',
            sale.number, request.user.username, exc,
        )
    except Exception:
        logger.exception('Unexpected error registering ticket for sale %s', pk)
        messages.error(request, 'Ocurrió un error inesperado. Intentá de nuevo.')

    return redirect('sales_web:sale_detail', pk=pk)

@login_required
@require_GET
def quote_print(request, pk):
    """
    Renderiza un HTML simplificado del presupuesto para impresión rápida (A4 o Ticket).
    
    GET /ventas/presupuestos/<pk>/imprimir/
    """
    quote = get_object_or_404(Quote, pk=pk)

    if not _owns_or_privileged(request.user, quote):
        messages.error(request, 'No tenés acceso a este presupuesto.')
        return redirect('sales_web:quote_list')

    context = {
        'quote': quote,
        'items': quote.items.select_related('product').order_by('line_order'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'BULONERA ALVEAR S.R.L.'),
        'company_cuit': getattr(settings, 'EMPRESA_CUIT', '')
    }

    return render(request, 'sales/quote_print.html', context)

@require_GET
def quote_public_view(request, uuid):
    """
    Renderiza una vista pública del presupuesto (sólo lectura).
    
    GET /ventas/presupuestos/publico/<uuid>/
    """
    quote = get_object_or_404(Quote, uuid=uuid)

    if quote.status == 'cancelled':
        raise Http404("El presupuesto ha sido cancelado y ya no está disponible.")

    context = {
        'quote': quote,
        'items': quote.items.select_related('product').order_by('line_order'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'BULONERA ALVEAR S.R.L.'),
        'company_cuit': getattr(settings, 'EMPRESA_CUIT', ''),
        'company_phone': getattr(settings, 'COMPANY_PHONE', '').replace('+', '').replace(' ', '').replace('-', '')
    }

    return render(request, 'sales/quote_public.html', context)

@require_GET
def quote_public_pdf_view(request, uuid):
    """
    Descargar o visualizar el presupuesto en PDF (público).
    
    GET /ventas/presupuestos/publico/<uuid>/pdf/
    """
    from sales.utils import generate_quote_pdf
    
    quote = get_object_or_404(Quote, uuid=uuid)

    if quote.status == 'cancelled':
        raise Http404("El presupuesto ha sido cancelado y ya no está disponible.")

    pdf_buffer = generate_quote_pdf(quote)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Presupuesto_{quote.number}.pdf"'
    return response