"""
bills/pdf.py — Generación de PDF de facturas electrónicas ARCA/AFIP

Cumple con:
  - RG 2485: Formato de comprobantes electrónicos
  - RG 4291: QR code obligatorio (desde 01/04/2021)
"""
import io
import json
import base64
from datetime import date
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Table, TableStyle
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


# ─── Layout ──────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ─── Tablas de constantes AFIP ────────────────────────────────────────────────

_LETRA = {
    1: 'A', 2: 'A', 3: 'A',
    6: 'B', 7: 'B', 8: 'B',
    11: 'C', 12: 'C', 13: 'C',
}
_TIPO = {
    1: 'FACTURA',   2: 'NOTA DE DÉBITO',   3: 'NOTA DE CRÉDITO',
    6: 'FACTURA',   7: 'NOTA DE DÉBITO',   8: 'NOTA DE CRÉDITO',
    11: 'FACTURA',  12: 'NOTA DE DÉBITO',  13: 'NOTA DE CRÉDITO',
}
_COND_IVA = {
    'RI': 'Responsable Inscripto',
    'MONO': 'Monotributista',
    'EX': 'Exento',
    'CF': 'Consumidor Final',
    'NR': 'No Responsable',
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(value) -> str:
    """Formatea Decimal como moneda argentina. Ej: $ 1.234,56"""
    v = Decimal(str(value or 0))
    neg = v < 0
    v = abs(v)
    int_part, dec_part = f'{v:.2f}'.split('.')
    int_fmt = '{:,}'.format(int(int_part)).replace(',', '.')
    result = f'$ {int_fmt},{dec_part}'
    return f'- {result}' if neg else result


def _build_qr_url(invoice) -> str:
    """URL del QR AFIP (RG 4291)."""
    comp = getattr(invoice, 'comprobante_arca', None)

    cuit_emisor = 20180545574
    if comp and comp.empresa_cuit_id:
        try:
            cuit_emisor = int(str(comp.empresa_cuit_id).replace('-', ''))
        except (ValueError, TypeError):
            pass

    doc_tipo, doc_nro = 99, 0
    if comp:
        doc_tipo = comp.doc_cliente_tipo or 99
        try:
            doc_nro = int(str(comp.doc_cliente or '0').replace('-', ''))
        except (ValueError, TypeError):
            doc_nro = 0

    fecha_str = (
        invoice.fecha_emision.strftime('%Y-%m-%d')
        if invoice.fecha_emision else date.today().strftime('%Y-%m-%d')
    )

    data = {
        "ver": 1,
        "fecha": fecha_str,
        "cuit": cuit_emisor,
        "ptoVta": invoice.punto_venta,
        "tipoCmp": invoice.tipo_comprobante,
        "nroCmp": invoice.numero_secuencial,
        "importe": float(invoice.total),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": doc_tipo,
        "nroDocRec": doc_nro,
        "tipoCodAut": "E",
        "codAut": int(invoice.cae) if invoice.cae else 0,
    }
    j = json.dumps(data, separators=(',', ':'))
    b64 = base64.urlsafe_b64encode(j.encode()).decode()
    return f"https://www.afip.gob.ar/fe/qr/?p={b64}"


def _draw_qr(c, url: str, x: float, y: float, size: float):
    """Dibuja el QR. Si qrcode no está instalado dibuja un placeholder."""
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10, border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, width=size, height=size, preserveAspectRatio=True)
    except ImportError:
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.3)
        c.rect(x, y, size, size)
        c.setFont('Helvetica', 6)
        c.setFillColor(colors.grey)
        c.drawCentredString(x + size / 2, y + size / 2 - 2 * mm, 'Instalar qrcode')
        c.drawCentredString(x + size / 2, y + size / 2 - 5 * mm, 'para el QR AFIP')
        c.setFillColor(colors.black)


def _draw_barcode(c, invoice, x, y, w, h):
    """Code 128 con datos del CAE."""
    if not invoice.cae:
        return
    comp = getattr(invoice, 'comprobante_arca', None)
    cuit = '20180545574'
    if comp and comp.empresa_cuit_id:
        cuit = str(comp.empresa_cuit_id).replace('-', '')

    vto = invoice.cae_vencimiento.strftime('%Y%m%d') if invoice.cae_vencimiento else '00000000'
    data = f'{cuit}{invoice.tipo_comprobante:02d}{invoice.punto_venta:04d}{invoice.numero_secuencial:08d}{invoice.cae}{vto}'

    try:
        bar = code128.Code128(data, barWidth=0.55, barHeight=h * 0.65, humanReadable=False)
        d = Drawing(w, h)
        bar.drawOn(d, 0, h * 0.15)
        renderPDF.draw(d, c, x, y)
    except Exception:
        pass


# ─── Función principal ────────────────────────────────────────────────────────

def generate_invoice_pdf(invoice) -> io.BytesIO:
    """
    Genera el PDF de una factura electrónica ARCA/AFIP.

    Args:
        invoice: bills.models.Invoice (preferentemente con estado_fiscal='autorizada')

    Returns:
        io.BytesIO con el PDF listo para enviar al navegador
    """
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'{_TIPO.get(invoice.tipo_comprobante, "Comprobante")} {invoice.number}')
    c.setAuthor('Bulonera Alvear S.R.L.')

    letra = _LETRA.get(invoice.tipo_comprobante, '?')
    tipo_nombre = _TIPO.get(invoice.tipo_comprobante, 'COMPROBANTE')

    # ── 1. CABECERA TRIPARTITA ────────────────────────────────────────────────
    HDR_H = 30 * mm
    BOX_W = 22 * mm
    BOX_X = PAGE_W / 2 - BOX_W / 2
    TOP_Y = PAGE_H - MARGIN
    HDR_Y = TOP_Y - HDR_H

    # Marco cabecera
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.6)
    c.rect(MARGIN, HDR_Y, CONTENT_W, HDR_H)

    # Caja central (letra)
    c.setLineWidth(1.5)
    c.rect(BOX_X, HDR_Y, BOX_W, HDR_H)
    c.setFont('Helvetica-Bold', 34)
    c.drawCentredString(BOX_X + BOX_W / 2, HDR_Y + HDR_H / 2 - 3 * mm, letra)
    c.setFont('Helvetica', 7)
    c.drawCentredString(BOX_X + BOX_W / 2, HDR_Y + 3 * mm, f'Cód. {invoice.tipo_comprobante:02d}')

    # Emisor (izquierda)
    ex, ey = MARGIN + 3 * mm, TOP_Y - 7 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(ex, ey, 'BULONERA ALVEAR S.R.L.')
    c.setFont('Helvetica', 7.5)
    c.drawString(ex, ey - 5 * mm, 'Av. Alvear 1234 — General Alvear, Mendoza')
    c.drawString(ex, ey - 9 * mm, 'CUIT: 20-18054557-4')
    c.drawString(ex, ey - 13 * mm, 'Ingresos Brutos: 1234567-89')
    c.drawString(ex, ey - 17 * mm, 'IVA Responsable Inscripto')
    c.drawString(ex, ey - 21 * mm, 'Inicio de actividades: 01/01/2000')

    # Comprobante (derecha)
    rx = BOX_X + BOX_W + 4 * mm
    ry = TOP_Y - 7 * mm
    c.setFont('Helvetica-Bold', 9)
    c.drawString(rx, ry, f'{tipo_nombre} {letra}')
    c.setFont('Helvetica-Bold', 10)
    c.drawString(rx, ry - 6 * mm, f'N°:  {invoice.number}')
    c.setFont('Helvetica', 8)
    fecha = invoice.fecha_emision.strftime('%d/%m/%Y') if invoice.fecha_emision else ''
    c.drawString(rx, ry - 12 * mm, f'Fecha de emisión:  {fecha}')
    if invoice.fecha_vto_pago:
        c.drawString(rx, ry - 16 * mm, f'Vto. pago:  {invoice.fecha_vto_pago.strftime("%d/%m/%Y")}')

    y = HDR_Y

    # ── 2. DATOS DEL RECEPTOR ─────────────────────────────────────────────────
    REC_H = 18 * mm
    REC_Y = y - REC_H
    c.setLineWidth(0.6)
    c.rect(MARGIN, REC_Y, CONTENT_W, REC_H)

    HALF = CONTENT_W / 2
    rx2, ry2 = MARGIN + 3 * mm, y - 6 * mm

    def _pair(label, value, lx, ly):
        c.setFont('Helvetica-Bold', 8)
        c.drawString(lx, ly, f'{label}:')
        c.setFont('Helvetica', 8)
        c.drawString(lx + 26 * mm, ly, str(value or '-'))

    _pair('Razón Social', invoice.cliente_razon_social or 'Consumidor Final', rx2, ry2)
    _pair('CUIT / DNI', invoice.cliente_cuit or '-', MARGIN + HALF + 3 * mm, ry2)
    _pair('Domicilio', invoice.cliente_domicilio or '-', rx2, ry2 - 5 * mm)
    _pair('Cond. IVA', _COND_IVA.get(invoice.cliente_condicion_iva, invoice.cliente_condicion_iva), MARGIN + HALF + 3 * mm, ry2 - 5 * mm)

    # Condición de pago
    pago = 'Contado'
    try:
        if invoice.sale and invoice.sale.customer and invoice.sale.customer.payment_term:
            pt = invoice.sale.customer.payment_term
            pago = 'Contado' if pt == 0 else f'{pt} días'
    except Exception:
        pass
    _pair('Cond. de pago', pago, rx2, ry2 - 10 * mm)

    y = REC_Y - 2 * mm

    # ── 3. TABLA DE ÍTEMS ─────────────────────────────────────────────────────
    items = list(invoice.items.all().order_by('numero_linea'))

    COL_W = [16 * mm, CONTENT_W - 16 * mm - 27 * mm - 22 * mm - 27 * mm, 27 * mm, 22 * mm, 27 * mm]

    rows = [['Cant.', 'Descripción', 'P. Unitario', 'Descuento', 'Subtotal']]
    for item in items:
        rows.append([
            f'{item.cantidad:.2f}',
            item.producto_nombre,
            _fmt(item.precio_unitario),
            _fmt(item.descuento) if item.descuento else '-',
            _fmt(item.subtotal),
        ])

    HEADER_BG = colors.HexColor('#1D4ED8')
    ALT_BG = colors.HexColor('#F8FAFC')

    t = Table(rows, colWidths=COL_W, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 8),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ALIGN',         (0, 0), (0, -1), 'CENTER'),
        ('ALIGN',         (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, ALT_BG]),
        ('GRID',          (0, 0), (-1, -1), 0.25, colors.HexColor('#E5E7EB')),
        ('LINEBELOW',     (0, 0), (-1, 0), 1, HEADER_BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]))

    t.wrapOn(c, CONTENT_W, y - MARGIN - 82 * mm)
    table_h = t._height
    t.drawOn(c, MARGIN, y - table_h)
    y = y - table_h - 3 * mm

    # ── 4. TOTALES ────────────────────────────────────────────────────────────
    TOT_W = 65 * mm
    TOT_X = PAGE_W - MARGIN - TOT_W
    TOT_RIGHT = PAGE_W - MARGIN

    rows_totals = [('Subtotal:', invoice.subtotal)]
    if invoice.descuento_total and invoice.descuento_total > 0:
        rows_totals.append(('Descuentos:', -invoice.descuento_total))
    rows_totals.append(('Neto gravado:', invoice.neto_gravado))
    rows_totals.append(('IVA 21%:', invoice.monto_iva))
    if invoice.monto_no_gravado and invoice.monto_no_gravado > 0:
        rows_totals.append(('No gravado:', invoice.monto_no_gravado))
    if invoice.monto_exento and invoice.monto_exento > 0:
        rows_totals.append(('Exento:', invoice.monto_exento))

    ty = y
    for label, value in rows_totals:
        c.setFont('Helvetica', 8)
        c.drawString(TOT_X, ty, label)
        c.drawRightString(TOT_RIGHT, ty, _fmt(value))
        ty -= 5 * mm

    # Línea y TOTAL
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)
    c.line(TOT_X, ty + 2 * mm, TOT_RIGHT, ty + 2 * mm)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(TOT_X, ty - 2 * mm, 'TOTAL:')
    c.drawRightString(TOT_RIGHT, ty - 2 * mm, _fmt(invoice.total))

    # Observaciones (izquierda, mismo bloque)
    if invoice.observaciones:
        c.setFont('Helvetica-Bold', 8)
        c.drawString(MARGIN, y, 'Observaciones:')
        c.setFont('Helvetica', 7.5)
        c.drawString(MARGIN, y - 5 * mm, invoice.observaciones[:120])

    # ── 5. FOOTER FISCAL ─────────────────────────────────────────────────────
    FOOTER_H = 38 * mm
    FOOTER_Y = MARGIN
    QR_SIZE = 30 * mm

    # Línea divisoria footer
    c.setStrokeColor(colors.HexColor('#9CA3AF'))
    c.setLineWidth(0.5)
    c.line(MARGIN, FOOTER_Y + FOOTER_H, MARGIN + CONTENT_W, FOOTER_Y + FOOTER_H)

    # QR AFIP (esquina inferior izquierda)
    if invoice.cae:
        qr_url = _build_qr_url(invoice)
        _draw_qr(c, qr_url, MARGIN, FOOTER_Y + (FOOTER_H - QR_SIZE) / 2, QR_SIZE)

    # Leyenda "Escanee con AFIP" debajo del QR
    c.setFont('Helvetica', 5.5)
    c.setFillColor(colors.HexColor('#6B7280'))
    c.drawCentredString(MARGIN + QR_SIZE / 2, FOOTER_Y + 2 * mm, 'Escanee con AFIP Móvil')
    c.setFillColor(colors.black)

    # Datos fiscales (al lado del QR)
    FX = MARGIN + QR_SIZE + 5 * mm
    FY = FOOTER_Y + FOOTER_H - 6 * mm

    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#1D4ED8'))
    c.drawString(FX, FY, 'COMPROBANTE ELECTRÓNICO AUTORIZADO POR AFIP / ARCA')
    c.setFillColor(colors.black)

    c.setFont('Helvetica', 8)
    c.drawString(FX, FY - 7 * mm, f'CAE N°: {invoice.cae or "-"}')
    vto_cae = invoice.cae_vencimiento.strftime('%d/%m/%Y') if invoice.cae_vencimiento else '-'
    c.drawString(FX, FY - 12 * mm, f'Vencimiento de CAE: {vto_cae}')

    # Código de barras Code 128
    BAR_W = CONTENT_W - QR_SIZE - 8 * mm
    BAR_H = 13 * mm
    BAR_Y = FOOTER_Y + 6 * mm
    if invoice.cae:
        _draw_barcode(c, invoice, FX, BAR_Y, BAR_W, BAR_H)
        # Valor legible debajo del barcode
        c.setFont('Helvetica', 6)
        c.setFillColor(colors.HexColor('#6B7280'))
        c.drawCentredString(FX + BAR_W / 2, FOOTER_Y + 2 * mm, invoice.cae)
        c.setFillColor(colors.black)

    c.showPage()
    c.save()

    buf.seek(0)
    return buf