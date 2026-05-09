"""
bills/pdf.py — Generación de PDF de facturas electrónicas ARCA/AFIP

Cumple con:
  - RG 2485: Formato de comprobantes electrónicos
  - RG 4291: QR code obligatorio (desde 01/04/2021)
"""
import io
import json
import base64
import os
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
    Genera el PDF de una factura electrónica ARCA/AFIP (Triplicado).
    """
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'{_TIPO.get(invoice.tipo_comprobante, "Comprobante")} {invoice.number}')
    
    from common.company import get_company_info
    empresa_info = get_company_info()
    c.setAuthor(empresa_info.get("razon_social") or empresa_info.get("name") or 'Mela Miguel Angel')

    letra = _LETRA.get(invoice.tipo_comprobante, '?')
    tipo_nombre = _TIPO.get(invoice.tipo_comprobante, 'COMPROBANTE')
    
    # Textos de contacto (hardcodeados o desde empresa_info)
    email_empresa = "contacto@buloneraalvear.online"
    whatsapp_empresa = "+5493624733431"

    COPIAS = ['ORIGINAL', 'DUPLICADO', 'TRIPLICADO']

    for copia in COPIAS:
        # Título superior (Original/Duplicado/Triplicado)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN + 4 * mm, copia)

        # ── 1. CABECERA TRIPARTITA ────────────────────────────────────────────────
        HDR_H = 35 * mm
        BOX_W = 22 * mm
        BOX_X = PAGE_W / 2 - BOX_W / 2
        TOP_Y = PAGE_H - MARGIN - 2 * mm
        HDR_Y = TOP_Y - HDR_H

        # Marco cabecera
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.rect(MARGIN, HDR_Y, CONTENT_W, HDR_H)

        # Caja central (letra)
        c.setLineWidth(1.5)
        c.rect(BOX_X, HDR_Y, BOX_W, HDR_H)
        c.setFont('Helvetica-Bold', 38)
        c.drawCentredString(BOX_X + BOX_W / 2, HDR_Y + HDR_H / 2 - 4 * mm, letra)
        c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(BOX_X + BOX_W / 2, HDR_Y + 3 * mm, f'Cód. {invoice.tipo_comprobante:02d}')

        # Emisor (izquierda)
        ex, ey = MARGIN + 3 * mm, TOP_Y - 5 * mm
        
        # Logo SVG (intento cargar con svglib si está disponible)
        logo_path = os.path.join('static', 'img', 'transpLOGO BULONERA.svg')
        if os.path.exists(logo_path):
            try:
                from svglib.svglib import svg2rlg
                drawing = svg2rlg(logo_path)
                if drawing:
                    # Escalar
                    scale = 0.08
                    drawing.width = drawing.minWidth() * scale
                    drawing.height = drawing.height * scale
                    drawing.scale(scale, scale)
                    renderPDF.draw(drawing, c, ex, ey - 15 * mm)
                    ex += 35 * mm # mover texto a la derecha del logo
            except ImportError:
                pass # si no hay svglib, no dibujar logo
        
        c.setFont('Helvetica-Bold', 11)
        c.drawString(ex, ey, (empresa_info.get("razon_social") or empresa_info.get("name") or "").upper())
        c.setFont('Helvetica', 7.5)
        c.drawString(ex, ey - 5 * mm, empresa_info.get("address", ""))
        c.drawString(ex, ey - 9 * mm, f'Email: {email_empresa}')
        c.drawString(ex, ey - 13 * mm, f'WhatsApp: {whatsapp_empresa}')
        
        iva_label = _COND_IVA.get(empresa_info.get('iva_condition', 'RI'), 'IVA Responsable Inscripto')
        c.setFont('Helvetica-Bold', 7.5)
        c.drawString(ex, ey - 19 * mm, iva_label)

        # Comprobante (derecha)
        rx = BOX_X + BOX_W + 4 * mm
        ry = TOP_Y - 5 * mm
        c.setFont('Helvetica-Bold', 12)
        c.drawString(rx, ry, f'{tipo_nombre}')
        c.setFont('Helvetica-Bold', 10)
        # Desagregar número de factura en punto de venta y comp nro
        nro_parts = invoice.number.split('-') if '-' in invoice.number else ['', invoice.number]
        pto_vta = f"{invoice.punto_venta:04d}" if hasattr(invoice, 'punto_venta') else (nro_parts[0].zfill(4) if nro_parts[0] else '0005')
        comp_nro = f"{invoice.numero_secuencial:08d}" if hasattr(invoice, 'numero_secuencial') else (nro_parts[1].zfill(8) if len(nro_parts)>1 else invoice.number.zfill(8))
        c.drawString(rx, ry - 6 * mm, f'Punto de Venta: {pto_vta}    Comp. Nro: {comp_nro}')
        
        c.setFont('Helvetica-Bold', 8)
        fecha = invoice.fecha_emision.strftime('%d/%m/%Y') if invoice.fecha_emision else ''
        c.drawString(rx, ry - 11 * mm, f'Fecha de Emisión: {fecha}')
        
        c.setFont('Helvetica', 8)
        cuit_empresa = empresa_info.get("cuit", "")
        if len(cuit_empresa) == 11 and '-' not in cuit_empresa:
            cuit_empresa = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}"
        c.drawString(rx, ry - 16 * mm, f'CUIT: {cuit_empresa}')
        c.drawString(rx, ry - 20 * mm, f'Ingresos Brutos: {empresa_info.get("ingresos_brutos", cuit_empresa)}')
        c.drawString(rx, ry - 24 * mm, f'Fecha de Inicio de Actividades: {empresa_info.get("inicio_actividades", "")}')

        y = HDR_Y

        # ── 2. DATOS DEL RECEPTOR ─────────────────────────────────────────────────
        REC_H = 18 * mm
        REC_Y = y - REC_H
        c.setLineWidth(0.6)
        c.rect(MARGIN, REC_Y, CONTENT_W, REC_H)

        HALF = CONTENT_W / 2
        rx2, ry2 = MARGIN + 3 * mm, y - 5 * mm

        def _pair(label, value, lx, ly):
            c.setFont('Helvetica-Bold', 8)
            c.drawString(lx, ly, f'{label}:')
            c.setFont('Helvetica', 8)
            c.drawString(lx + 26 * mm, ly, str(value or '-'))

        _pair('CUIT / DNI', invoice.cliente_cuit or '-', rx2, ry2)
        _pair('Razón Social', invoice.cliente_razon_social or 'Consumidor Final', MARGIN + HALF + 3 * mm, ry2)
        
        _pair('Cond. IVA', _COND_IVA.get(invoice.cliente_condicion_iva, invoice.cliente_condicion_iva), rx2, ry2 - 5 * mm)
        _pair('Domicilio', invoice.cliente_domicilio or '-', MARGIN + HALF + 3 * mm, ry2 - 5 * mm)

        # Condición de pago
        pago = 'Contado'
        try:
            if invoice.sale and invoice.sale.customer and invoice.sale.customer.payment_term:
                pt = invoice.sale.customer.payment_term
                pago = 'Contado' if pt == 0 else f'{pt} días'
        except Exception:
            pass
        _pair('Cond. de venta', pago, rx2, ry2 - 10 * mm)

        y = REC_Y - 2 * mm

        # ── 3. TABLA DE ÍTEMS ─────────────────────────────────────────────────────
        items = list(invoice.items.all().order_by('numero_linea'))

        # Columnas: Codigo, Descripcion, Cantidad, Unidad de Medida, Precio Unitario, Bonificación, Subtotal (s/iva), alicuota, SUBTOTAL C/IVA
        COL_W = [18 * mm, CONTENT_W - 146 * mm, 14 * mm, 16 * mm, 20 * mm, 20 * mm, 22 * mm, 14 * mm, 22 * mm]

        rows = [['Código', 'Descripción', 'Cant.', 'U. Medida', 'P. Unit.', '% Bonif', 'Subt. s/IVA', 'Alic.', 'Subt. c/IVA']]
        for item in items:
            # Calcular subtotal sin iva
            alicuota_val = getattr(item, 'alicuota_iva', 21) or 21
            # item.subtotal es el monto con iva? No, en InvoiceItem subtotal suele ser neto, vamos a ver
            # si en InvoiceItem está subtotal, precio_unitario, descuento, monto_iva, total
            # En bills/pdf.py original el Subtotal era item.subtotal.
            subt_neto = getattr(item, 'subtotal', 0)
            alicuota_str = f"{alicuota_val}%"
            subt_c_iva = subt_neto + getattr(item, 'monto_iva', 0)
            if hasattr(item, 'total'):
                subt_c_iva = item.total

            bonif = _fmt(item.descuento) if item.descuento else '-'
            
            codigo = getattr(item, 'producto_codigo', '') or getattr(item, 'producto_sku', '')
            if not codigo and hasattr(item, 'product') and hasattr(item.product, 'sku'):
                codigo = item.product.sku

            rows.append([
                codigo[:15],
                item.producto_nombre[:45],
                f'{item.cantidad:.2f}',
                'unidades', # O unidad de medida real si existe
                _fmt(item.precio_unitario),
                bonif,
                _fmt(subt_neto),
                alicuota_str,
                _fmt(subt_c_iva),
            ])

        HEADER_BG = colors.HexColor('#E5E7EB')
        ALT_BG = colors.HexColor('#F8FAFC')

        t = Table(rows, colWidths=COL_W, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR',     (0, 0), (-1, 0), colors.black),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0), 7),
            ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',      (0, 1), (-1, -1), 7),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN',         (1, 1), (1, -1), 'LEFT'), # Descripcion
            ('ALIGN',         (4, 1), (8, -1), 'RIGHT'), # Precios
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, ALT_BG]),
            ('GRID',          (0, 0), (-1, -1), 0.25, colors.HexColor('#D1D5DB')),
            ('LINEBELOW',     (0, 0), (-1, 0), 1, colors.black),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ]))

        # Límite vertical para que los items no tapen los tributos
        t.wrapOn(c, CONTENT_W, y - MARGIN - 100 * mm)
        table_h = t._height
        t.drawOn(c, MARGIN, y - table_h)
        y = y - table_h - 3 * mm

        # ── 4. TRIBUTOS ────────────────────────────────────────────────────────────
        TRIB_H = 35 * mm
        TRIB_Y = MARGIN + 40 * mm # Dejamos espacio para el footer fiscal
        c.setLineWidth(0.6)
        c.rect(MARGIN, TRIB_Y, CONTENT_W, TRIB_H)

        c.setFont('Helvetica-Bold', 8)
        c.drawString(MARGIN + 3 * mm, TRIB_Y + TRIB_H - 5 * mm, "Importe Neto Gravado:")
        c.setFont('Helvetica', 8)
        c.drawRightString(MARGIN + 45 * mm, TRIB_Y + TRIB_H - 5 * mm, _fmt(invoice.neto_gravado))

        # IVA desglose
        # Agrupamos por alicuotas o mostramos fijas como pidió el usuario
        # IVA 27, 21, 10.5, 5, 2.5, 0
        ivas = {27: 0, 21: 0, 10.5: 0, 5: 0, 2.5: 0, 0: 0}
        
        # Intentamos obtener desglose real si lo guardamos (en invoice o renglones)
        for it in items:
            ali = getattr(it, 'alicuota_iva', 21) or 0
            m_iva = getattr(it, 'monto_iva', 0)
            if ali in ivas:
                ivas[ali] += m_iva
            else:
                ivas[ali] = m_iva
                
        ly = TRIB_Y + TRIB_H - 10 * mm
        lx = MARGIN + 3 * mm
        for pct in [27, 21, 10.5, 5, 2.5, 0]:
            val = ivas.get(pct, 0)
            c.setFont('Helvetica-Bold', 7)
            c.drawString(lx, ly, f"IVA {pct}%:")
            c.setFont('Helvetica', 7)
            c.drawRightString(lx + 42 * mm, ly, _fmt(val))
            ly -= 4 * mm
            
        c.setFont('Helvetica-Bold', 8)
        c.drawString(MARGIN + CONTENT_W / 2 + 10 * mm, TRIB_Y + TRIB_H - 5 * mm, "Importe Otros Tributos:")
        c.setFont('Helvetica', 8)
        otros_tributos = getattr(invoice, 'monto_tributos', 0)
        c.drawRightString(MARGIN + CONTENT_W - 5 * mm, TRIB_Y + TRIB_H - 5 * mm, _fmt(otros_tributos))

        c.setFont('Helvetica-Bold', 12)
        c.drawString(MARGIN + CONTENT_W / 2 + 10 * mm, TRIB_Y + 10 * mm, "IMPORTE TOTAL:")
        c.drawRightString(MARGIN + CONTENT_W - 5 * mm, TRIB_Y + 10 * mm, _fmt(invoice.total))


        # ── 5. FOOTER FISCAL Y CONTACTO ──────────────────────────────────────────
        FOOTER_H = 38 * mm
        FOOTER_Y = MARGIN
        QR_SIZE = 30 * mm

        # Datos de Contacto (Redes)
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(colors.HexColor('#1F2937'))
        contacto_str = " | ".join([
            f"EMAIL: {email_empresa}",
            f"WHATSAPP: {whatsapp_empresa}",
            "INSTAGRAM: @buloneraalvear",
            "FACEBOOK: Bulonera Alvear"
        ])
        c.drawCentredString(PAGE_W / 2, FOOTER_Y + FOOTER_H - 3 * mm, contacto_str)
        c.setFillColor(colors.black)

        # Línea divisoria footer fiscal
        c.setStrokeColor(colors.HexColor('#9CA3AF'))
        c.setLineWidth(0.5)
        c.line(MARGIN, FOOTER_Y + FOOTER_H - 5 * mm, MARGIN + CONTENT_W, FOOTER_Y + FOOTER_H - 5 * mm)

        # QR AFIP
        if invoice.cae:
            qr_url = _build_qr_url(invoice)
            _draw_qr(c, qr_url, MARGIN, FOOTER_Y + 2 * mm, QR_SIZE - 4 * mm)

        # Leyenda "Escanee con AFIP"
        c.setFont('Helvetica', 5.5)
        c.setFillColor(colors.HexColor('#6B7280'))
        c.drawCentredString(MARGIN + QR_SIZE / 2, FOOTER_Y + 1 * mm, 'Escanee con AFIP Móvil')
        c.setFillColor(colors.black)

        # Datos fiscales
        FX = MARGIN + QR_SIZE + 5 * mm
        FY = FOOTER_Y + 25 * mm

        c.setFont('Helvetica-Bold', 8)
        c.setFillColor(colors.HexColor('#1D4ED8'))
        c.drawString(FX, FY, 'COMPROBANTE ELECTRÓNICO AUTORIZADO POR AFIP / ARCA')
        c.setFillColor(colors.black)

        c.setFont('Helvetica', 8)
        c.drawString(FX, FY - 6 * mm, f'CAE N°: {invoice.cae or "-"}')
        vto_cae = invoice.cae_vencimiento.strftime('%d/%m/%Y') if invoice.cae_vencimiento else '-'
        c.drawString(FX, FY - 11 * mm, f'Vencimiento de CAE: {vto_cae}')

        # Código de barras Code 128
        BAR_W = CONTENT_W - QR_SIZE - 8 * mm
        BAR_H = 13 * mm
        BAR_Y = FOOTER_Y + 5 * mm
        if invoice.cae:
            _draw_barcode(c, invoice, FX, BAR_Y, BAR_W, BAR_H)
            c.setFont('Helvetica', 6)
            c.setFillColor(colors.HexColor('#6B7280'))
            c.drawCentredString(FX + BAR_W / 2, FOOTER_Y + 1 * mm, invoice.cae)
            c.setFillColor(colors.black)

        c.showPage()
    
    c.save()
    buf.seek(0)
    return buf
