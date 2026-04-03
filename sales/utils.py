import io
import datetime
from decimal import Decimal
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from common.company import get_company_info

try:
    from bills.pdf import _fmt
except ImportError:
    def _fmt(val):
        """Formatea un número o Decimal a moneda argentina ($ X.XXX,XX)."""
        if val is None:
            return "$ 0,00"
        try:
            val = float(val)
        except (ValueError, TypeError):
            return "$ 0,00"
        
        # Formato con coma y sin separador de miles primero
        s = f"{val:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${s}"

def generate_quote_pdf(quote) -> io.BytesIO:
    """
    Genera un PDF del presupuesto usando ReportLab.

    Args:
        quote: Instancia de sales.Quote con items precargados

    Returns:
        io.BytesIO: Buffer del PDF listo para adjuntar o descargar
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    PAGE_W, PAGE_H = A4
    MARGIN = 15 * mm

    # 1. Cabecera
    c.setFont("Helvetica-Bold", 14)
    company_info = get_company_info()
    company_name = company_info['name']
    c.drawString(MARGIN, PAGE_H - MARGIN - 10, company_name)
    
    c.setFont("Helvetica", 10)
    company_cuit = company_info['cuit']
    if company_cuit:
        c.drawString(MARGIN, PAGE_H - MARGIN - 25, f"CUIT: {company_cuit}")
    
    # Datos comprobante
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 10, f"PRESUPUESTO Nº {quote.number}")
    
    c.setFont("Helvetica", 10)
    fecha_str = quote.date.strftime('%d/%m/%Y') if quote.date else ''
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 25, f"Fecha: {fecha_str}")
    
    if quote.valid_until:
        valido_str = quote.valid_until.strftime('%d/%m/%Y')
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 40, f"Válido hasta: {valido_str}")

    # 3. Datos cliente
    y_cliente = PAGE_H - MARGIN - 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y_cliente, "Cliente:")
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN + 45, y_cliente, str(quote.customer_display))

    y_cliente -= 15
    cuit = quote.customer_cuit or getattr(quote.customer, 'cuit_cuil', '')
    if cuit:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN, y_cliente, "CUIT/CUIL:")
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN + 60, y_cliente, str(cuit))

    # 4. Tabla de items
    y_table = y_cliente - 20

    data = [['Cant', 'Descripción', 'P. Unit', 'Descuento', 'Subtotal']]
    
    for item in quote.items.all().order_by('line_order'):
        cant = f"{item.quantity:g}"
        desc = getattr(item.product, 'name', str(item.product))[:50]
        # P. Unit
        p_unit = _fmt(item.unit_price)
        # Desc
        desc_val = f"-{_fmt(item.discount_amount)}" if item.discount_amount and item.discount_amount > 0 else "—"
        # Subtotal
        subt = _fmt(item.subtotal_with_discount)
        
        data.append([cant, desc, p_unit, desc_val, subt])

    table = Table(data, colWidths=[15*mm, 85*mm, 25*mm, 25*mm, 30*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
    ]))

    w, h = table.wrap(PAGE_W - 2*MARGIN, y_table)
    table.drawOn(c, MARGIN, y_table - h)

    # 5. Totales
    y_totales = y_table - h - 15
    c.setFont("Helvetica", 10)
    
    subtotal = _fmt(quote._cached_subtotal)
    c.drawRightString(PAGE_W - MARGIN - 35, y_totales, "Subtotal:")
    c.drawRightString(PAGE_W - MARGIN, y_totales, subtotal)
    
    if hasattr(quote, '_cached_discount') and quote._cached_discount > 0:
        y_totales -= 15
        desc_tot = _fmt(quote._cached_discount)
        c.drawRightString(PAGE_W - MARGIN - 35, y_totales, "Descuentos:")
        c.drawRightString(PAGE_W - MARGIN, y_totales, f"-{desc_tot}")

    y_totales -= 15
    tax = getattr(quote, '_cached_tax', Decimal('0'))
    iva = _fmt(tax)
    c.drawRightString(PAGE_W - MARGIN - 35, y_totales, "IVA:")
    c.drawRightString(PAGE_W - MARGIN, y_totales, iva)

    y_totales -= 20
    c.setFont("Helvetica-Bold", 12)
    tot = _fmt(quote._cached_total)
    c.drawRightString(PAGE_W - MARGIN - 35, y_totales, "TOTAL:")
    c.drawRightString(PAGE_W - MARGIN, y_totales, tot)

    # 6. Pie de página
    y_pie = 30 * mm
    c.setFont("Helvetica", 8)
    c.setStrokeColor(colors.HexColor('#cbd5e1'))
    c.line(MARGIN, y_pie + 10, PAGE_W - MARGIN, y_pie + 10)
    
    if quote.notes:
        c.drawString(MARGIN, y_pie, "Notas:")
        c.drawString(MARGIN, y_pie - 10, str(quote.notes)[:150])
    
    if quote.valid_until:
        valido_str = quote.valid_until.strftime('%d/%m/%Y')
        c.drawCentredString(PAGE_W / 2, 15 * mm, f"Este presupuesto es válido hasta el {valido_str}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
