"""
sales/utils.py — Generación de comprobantes y utilidades para ventas y presupuestos.
"""
import io
import os
from decimal import Decimal
from datetime import date

from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics import renderPDF

from common.company import get_company_info
from common.utils import format_quantity

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
        s = f"{val:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"$ {s}"


def generate_quote_pdf(quote) -> io.BytesIO:
    """
    Genera el PDF del presupuesto usando ReportLab con la estructura
    oficial de comprobante clase 'X' (tipo factura argentina).

    Args:
        quote: Instancia de sales.Quote con items precargados

    Returns:
        io.BytesIO: Buffer del PDF listo para descargar o adjuntar
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    PAGE_W, PAGE_H = A4
    MARGIN = 15 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN

    c.setTitle(f"Presupuesto {quote.number}")
    
    empresa_info = get_company_info()
    c.setAuthor(empresa_info.get("razon_social") or empresa_info.get("name") or "Bulonera Alvear")

    # Estilos de ReportLab
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    
    style_emisor = ParagraphStyle(
        'EmisorQuote', parent=style_normal, fontName='Helvetica', fontSize=7.5, leading=9.5
    )
    style_comp = ParagraphStyle(
        'CompQuote', parent=style_normal, fontName='Helvetica', fontSize=7.5, leading=10
    )
    style_rec = ParagraphStyle(
        'RecQuote', parent=style_normal, fontName='Helvetica', fontSize=8, leading=10
    )
    style_item_desc = ParagraphStyle(
        'ItemDescQuote', parent=style_normal, fontName='Helvetica', fontSize=7.5, leading=9
    )
    style_notes = ParagraphStyle(
        'NotesQuote', parent=style_normal, fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#334155')
    )

    # ── 0. BANNER SUPERIOR ──────────────────────────────────────────────────
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#b91c1c'))
    c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN + 2 * mm, "DOCUMENTO NO VÁLIDO COMO FACTURA")
    c.setFillColor(colors.black)

    # ── 1. CABECERA TRIPARTITA ────────────────────────────────────────────────
    HDR_H = 34 * mm
    BOX_W = 20 * mm   # Ancho caja de letra
    BOX_H = 18 * mm   # Alto caja de letra
    BOX_X = PAGE_W / 2 - BOX_W / 2
    TOP_Y = PAGE_H - MARGIN - 1 * mm
    HDR_Y = TOP_Y - HDR_H
    BOX_Y = TOP_Y - BOX_H

    # Marco cabecera
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.6)
    c.rect(MARGIN, HDR_Y, CONTENT_W, HDR_H)

    # Caja central (letra 'X')
    c.setLineWidth(1.2)
    c.rect(BOX_X, BOX_Y, BOX_W, BOX_H)
    c.setFont('Helvetica-Bold', 30)
    c.drawCentredString(BOX_X + BOX_W / 2, BOX_Y + 5.5 * mm, "X")
    
    c.setFont('Helvetica-Bold', 4.8)
    c.drawCentredString(BOX_X + BOX_W / 2, BOX_Y + 2.8 * mm, "NO VÁLIDO COMO FACTURA")
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(BOX_X + BOX_W / 2, BOX_Y + 1 * mm, "CÓD. 000")

    # Línea vertical divisoria debajo de la caja de letra
    c.setLineWidth(0.6)
    c.line(PAGE_W / 2, HDR_Y, PAGE_W / 2, BOX_Y)

    # Emisor (izquierda)
    razon_social_str = (empresa_info.get("razon_social") or empresa_info.get("name") or "BULONERA ALVEAR").upper()
    nombre_fantasia = empresa_info.get("name") or "BULONERA ALVEAR"
    domicilio_empresa = empresa_info.get("address") or "Av. Alvear 1234, Resistencia - Chaco"
    telefono_empresa = empresa_info.get("phone") or "+54 9 362 473-3431"
    email_empresa = empresa_info.get("email") or "contacto@buloneraalvear.online"
    cond_iva_empresa = empresa_info.get("iva_condition") or "IVA Responsable Inscripto"

    emisor_html = f"""
    <b><font size="11" color="#1B3A5C">{nombre_fantasia}</font></b><br/>
    <b>Razón Social:</b> {razon_social_str}<br/>
    <b>Domicilio:</b> {domicilio_empresa}<br/>
    <b>Tel/WhatsApp:</b> {telefono_empresa} &nbsp; <b>Email:</b> {email_empresa}<br/>
    <b>{cond_iva_empresa}</b>
    """
    
    emisor_p = Paragraph(emisor_html, style_emisor)
    emisor_table = Table([[emisor_p]], colWidths=[BOX_X - MARGIN - 2 * mm])
    emisor_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    emisor_table.wrapOn(c, BOX_X - MARGIN - 2 * mm, HDR_H)
    emisor_table.drawOn(c, MARGIN + 2 * mm, HDR_Y + 3 * mm)

    # Comprobante Presupuesto (derecha)
    pto_vta = f"{empresa_info.get('punto_venta', 1):04d}"
    comp_nro = str(quote.number)
    fecha_str = quote.date.strftime('%d/%m/%Y') if quote.date else date.today().strftime('%d/%m/%Y')
    validez_str = quote.valid_until.strftime('%d/%m/%Y') if quote.valid_until else "15 días"
    
    cuit_empresa = empresa_info.get("cuit", "")
    if len(cuit_empresa) == 11 and '-' not in cuit_empresa:
        cuit_empresa = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}"

    iibb_str = empresa_info.get("ingresos_brutos") or cuit_empresa or "-"
    inicio_act_str = empresa_info.get("inicio_actividades") or "-"

    comp_html = f"""
    <font size="12"><b>PRESUPUESTO</b></font><br/>
    <b>Punto de Venta:</b> {pto_vta} &nbsp; <b>Comp. Nro:</b> {comp_nro}<br/>
    <b>Fecha de Emisión:</b> {fecha_str}<br/>
    <b>Validez de Oferta:</b> {validez_str}<br/>
    <b>CUIT:</b> {cuit_empresa} &nbsp; <b>IIBB:</b> {iibb_str}<br/>
    <b>Inicio Actividades:</b> {inicio_act_str}
    """

    comp_p = Paragraph(comp_html, style_comp)
    comp_table = Table([[comp_p]], colWidths=[CONTENT_W - (BOX_X + BOX_W - MARGIN) - 2 * mm])
    comp_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    comp_table.wrapOn(c, CONTENT_W - (BOX_X + BOX_W - MARGIN) - 2 * mm, HDR_H)
    comp_table.drawOn(c, BOX_X + BOX_W + 3 * mm, HDR_Y + 2 * mm)

    y_cursor = HDR_Y

    # ── 2. DATOS DEL CLIENTE / RECEPTOR ───────────────────────────────────────
    REC_H = 18 * mm
    REC_Y = y_cursor - REC_H - 2 * mm
    c.setLineWidth(0.6)
    c.rect(MARGIN, REC_Y, CONTENT_W, REC_H)

    cuit_cli = quote.customer_cuit or getattr(quote.customer, 'cuit_cuil', '') or '-'
    razon_cli = str(quote.customer_display)
    cond_iva_cli = "Consumidor Final"
    if quote.customer and hasattr(quote.customer, 'get_iva_condition_display'):
        cond_iva_cli = quote.customer.get_iva_condition_display()
    
    domicilio_cli = getattr(quote.customer, 'address', '') or '-'
    vendedor_str = quote.created_by.get_full_name() if quote.created_by else (getattr(quote.created_by, 'username', 'Mostrador'))

    rec_data = [
        [
            Paragraph(f"<b>Cliente / Razón Social:</b> {razon_cli}", style_rec),
            Paragraph(f"<b>Condición de Venta:</b> Contado / Cta Cte", style_rec)
        ],
        [
            Paragraph(f"<b>CUIT / CUIL / DNI:</b> {cuit_cli}", style_rec),
            Paragraph(f"<b>Domicilio:</b> {domicilio_cli}", style_rec)
        ],
        [
            Paragraph(f"<b>Condición IVA:</b> {cond_iva_cli}", style_rec),
            Paragraph(f"<b>Vendedor:</b> {vendedor_str}", style_rec)
        ]
    ]

    rec_table = Table(rec_data, colWidths=[CONTENT_W * 0.58, CONTENT_W * 0.42])
    rec_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2 * mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 2 * mm),
        ('TOPPADDING', (0,0), (-1,-1), 0.5 * mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.5 * mm),
    ]))
    rec_table.wrapOn(c, CONTENT_W, REC_H)
    rec_table.drawOn(c, MARGIN, REC_Y + 1 * mm)

    y_cursor = REC_Y

    # ── 3. TABLA DE CONCEPTOS / ITEMS ─────────────────────────────────────────
    y_table_top = y_cursor - 3 * mm

    table_data = [[
        Paragraph("<b>Cant.</b>", style_comp),
        Paragraph("<b>Código</b>", style_comp),
        Paragraph("<b>Descripción / Concepto</b>", style_comp),
        Paragraph("<b>P. Unitario</b>", style_comp),
        Paragraph("<b>Bonif.</b>", style_comp),
        Paragraph("<b>Subtotal</b>", style_comp)
    ]]

    for item in quote.items.all().order_by('line_order'):
        cant = format_quantity(item.quantity)
        code = getattr(item.product, 'sku', '') or getattr(item.product, 'code', '') or '-'
        p_name = getattr(item.product, 'name', str(item.product))
        if item.discount_reason:
            desc_p = Paragraph(f"<b>{p_name}</b><br/><font size=6 color='#64748b'>({item.discount_reason})</font>", style_item_desc)
        else:
            desc_p = Paragraph(f"<b>{p_name}</b>", style_item_desc)
        
        p_unit = _fmt(item.unit_price)
        desc_val = f"-{_fmt(item.discount_amount)}" if item.discount_amount and item.discount_amount > 0 else "—"
        subt = _fmt(item.subtotal_with_discount)

        table_data.append([
            cant,
            code,
            desc_p,
            p_unit,
            desc_val,
            subt
        ])

    col_widths = [14 * mm, 24 * mm, 80 * mm, 22 * mm, 18 * mm, 22 * mm]
    # Normalizar ancho al ancho de contenido
    scale_factor = CONTENT_W / sum(col_widths)
    adjusted_col_widths = [w * scale_factor for w in col_widths]

    items_table = Table(table_data, colWidths=adjusted_col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'LEFT'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7.5),
        ('TOPPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('LEFTPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BOX', (0,0), (-1,-1), 0.8, colors.black),
    ]))

    w, h_table = items_table.wrap(CONTENT_W, y_table_top - 60 * mm)
    y_table_bottom = y_table_top - h_table
    items_table.drawOn(c, MARGIN, y_table_bottom)

    y_cursor = y_table_bottom - 4 * mm

    # ── 4. SECCIÓN INFERIOR: NOTAS Y TOTALES ──────────────────────────────────
    TOTALS_W = 68 * mm
    NOTES_W = CONTENT_W - TOTALS_W - 4 * mm
    SEC_H = 26 * mm
    SEC_Y = y_cursor - SEC_H

    # Cuadro de notas (Izquierda)
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor('#94a3b8'))
    c.rect(MARGIN, SEC_Y, NOTES_W, SEC_H)
    
    notes_text = quote.notes or "• Precios válidos hasta la fecha de vigencia indicada.\n• Cotización sujeta a disponibilidad de stock al momento de la confirmación.\n• Documento emitido con fines informativos comerciales."
    notes_p = Paragraph(f"<b>Observaciones y Condiciones Comerciales:</b><br/>{notes_text.replace(chr(10), '<br/>')}", style_notes)
    notes_table = Table([[notes_p]], colWidths=[NOTES_W - 2 * mm])
    notes_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 1 * mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 1 * mm),
        ('TOPPADDING', (0,0), (-1,-1), 1 * mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1 * mm),
    ]))
    notes_table.wrapOn(c, NOTES_W - 2 * mm, SEC_H)
    notes_table.drawOn(c, MARGIN + 1 * mm, SEC_Y + 1 * mm)

    # Cuadro de totales (Derecha)
    subtotal_val = _fmt(quote._cached_subtotal)
    discount_val = _fmt(quote._cached_discount) if hasattr(quote, '_cached_discount') and quote._cached_discount > 0 else None
    tax_val = _fmt(quote._cached_tax) if hasattr(quote, '_cached_tax') and quote._cached_tax > 0 else None
    total_val = _fmt(quote._cached_total)

    tot_rows = [
        [Paragraph("<b>Subtotal:</b>", style_comp), Paragraph(f"<b>{subtotal_val}</b>", style_comp)]
    ]
    if discount_val:
        tot_rows.append([
            Paragraph("<b>Descuentos:</b>", style_comp),
            Paragraph(f"<font color='#b91c1c'><b>-{discount_val}</b></font>", style_comp)
        ])
    if tax_val:
        tot_rows.append([
            Paragraph("<b>IVA:</b>", style_comp),
            Paragraph(f"<b>{tax_val}</b>", style_comp)
        ])
    tot_rows.append([
        Paragraph("<font size=9><b>TOTAL:</b></font>", style_comp),
        Paragraph(f"<font size=10 color='#1B3A5C'><b>{total_val}</b></font>", style_comp)
    ])

    tot_table = Table(tot_rows, colWidths=[TOTALS_W * 0.45, TOTALS_W * 0.55])
    tot_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1 * mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1 * mm),
        ('LEFTPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 1.5 * mm),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 0.8, colors.black),
    ]))
    tot_table.wrapOn(c, TOTALS_W, SEC_H)
    tot_table.drawOn(c, MARGIN + NOTES_W + 4 * mm, SEC_Y)

    # ── 5. PIE DE PÁGINA LEGAL ────────────────────────────────────────────────
    FOOTER_H = 10 * mm
    FOOTER_Y = MARGIN
    c.setLineWidth(0.6)
    c.setStrokeColor(colors.black)
    c.rect(MARGIN, FOOTER_Y, CONTENT_W, FOOTER_H)

    c.setFont('Helvetica-Bold', 7.5)
    c.setFillColor(colors.HexColor('#b91c1c'))
    c.drawCentredString(PAGE_W / 2, FOOTER_Y + 5.5 * mm, "DOCUMENTO NO VÁLIDO COMO FACTURA — COMPROBANTE CLASE \"X\"")
    
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.HexColor('#475569'))
    validez_footer = f"Oferta válida hasta el {validez_str} | " if validez_str else ""
    c.drawCentredString(PAGE_W / 2, FOOTER_Y + 2 * mm, f"ERP Bulonera Alvear | {validez_footer}Página 1 de 1")
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
