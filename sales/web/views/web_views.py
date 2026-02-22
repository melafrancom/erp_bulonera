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
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from sales.models import Quote, QuoteItem, Sale, SaleItem
from sales.services import cancel_sale, confirm_sale, convert_quote_to_sale

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
        )

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
    if not _can_manage_quotes(request.user):
        messages.error(request, 'No tenés permisos para crear presupuestos.')
        return redirect('sales_web:quote_list')

    # Lazy imports: products y customers pueden no estar disponibles aún
    customers = _get_customers_queryset()
    products  = _get_products_queryset()

    context = {
        'customers': customers,
        'products':  products,
        'today':     timezone.now().date(),
        'mode':      'create',
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
        'quote':     quote,
        'items':     quote.items.select_related('product').order_by('line_order'),
        'customers': customers,
        'products':  products,
        'mode':      'update',
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
        )

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
    if not _can_manage_sales(request.user):
        messages.error(request, 'No tenés permisos para crear ventas.')
        return redirect('sales_web:sale_list')

    customers = _get_customers_queryset()
    products  = _get_products_queryset()

    context = {
        'customers': customers,
        'products':  products,
        'today':     timezone.now().date(),
        'mode':      'create',
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

    # Transiciones válidas desde esta vista
    VALID_TRANSITIONS = {
        'confirmed':      'in_preparation',
        'in_preparation': 'ready',
        'ready':          'delivered',
    }

    new_status = request.POST.get('new_status', '').strip()
    expected   = VALID_TRANSITIONS.get(sale.status)

    if not expected:
        messages.error(
            request,
            f'La venta en estado "{sale.get_status_display()}" no puede avanzar.'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    if new_status != expected:
        messages.error(
            request,
            f'Transición inválida: no se puede pasar de '
            f'"{sale.get_status_display()}" a "{new_status}".'
        )
        return redirect('sales_web:sale_detail', pk=pk)

    try:
        sale.status = new_status

        # Agregar nota de entrega si se proporciona
        if new_status == 'delivered':
            delivery_notes = request.POST.get('delivery_notes', '').strip()
            if delivery_notes:
                ts = timezone.now().strftime('%d/%m/%Y %H:%M')
                sale.internal_notes = (
                    f'{sale.internal_notes}\n\n'
                    f'[{ts}] Entregado por {request.user.get_full_name() or request.user.username}: '
                    f'{delivery_notes}'
                ).strip()

        sale.save(update_fields=['status', 'internal_notes'])

        messages.success(
            request,
            f'Venta {sale.number} movida a "{sale.get_status_display()}".'
        )
        logger.info(
            'Sale %s moved to %s by user %s',
            sale.number, new_status, request.user.username,
        )

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