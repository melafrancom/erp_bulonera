import io
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_invoice_pdf(invoice):
    """
    Genera un PDF (en memoria) para la factura dada utilizando ReportLab.
    Retorna el buffer (io.BytesIO) con el contenido del PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=f"Factura {invoice.number}"
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH1 = styles["Heading1"]
    styleH1.alignment = 1 # Center
    
    # Contenido del documento (lista de elementos Platypus)
    elements = []
    
    # Titulo y Letra Factura
    tipo_comprob_letra = "B"
    if invoice.tipo_comprobante in [1, 2, 3]:
        tipo_comprob_letra = "A"
        
    elements.append(Paragraph(f"<b>FACTURA '{tipo_comprob_letra}'</b>", styleH1))
    elements.append(Spacer(1, 5*mm))
    
    # Cabecera Empresa - Factura
    header_data = [
        [
            Paragraph("<b>BULONERA ALVEAR S.R.L.</b>", styleN), 
            Paragraph(f"<b>Comprobante:</b> {invoice.number}<br/><b>Fecha de Emisión:</b> {invoice.fecha_emision.strftime('%d/%m/%Y')}", styleN)
        ],
        [
            Paragraph("Av. Alvear 1234, General Alvear, Mendoza<br/>IVA Responsable Inscripto", styleN),
            Paragraph(f"<b>CUIT:</b> 30-12345678-9<br/><b>Ingresos Brutos:</b> 1234567-89", styleN)
        ]
    ]
    t_header = Table(header_data, colWidths=[90*mm, 90*mm])
    t_header.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 5*mm))
    
    # Datos del Cliente
    client_data = [
        [
            Paragraph(f"<b>Señor(es):</b> {invoice.cliente_razon_social}", styleN),
            Paragraph(f"<b>CUIT:</b> {invoice.cliente_cuit or 'Consumidor Final'}", styleN)
        ],
        [
            Paragraph(f"<b>Domicilio:</b> {invoice.cliente_domicilio or '-'}", styleN),
            Paragraph(f"<b>Condición IVA:</b> {invoice.cliente_condicion_iva}", styleN)
        ]
    ]
    t_client = Table(client_data, colWidths=[90*mm, 90*mm])
    t_client.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_client)
    elements.append(Spacer(1, 5*mm))
    
    # Items (Detalle)
    item_data = [["Código", "Descripción", "Cant.", "P.Unit.", "Desc.", "Subtotal"]]
    for item in invoice.items.all():
        item_data.append([
            item.producto_codigo or "",
            item.producto_nombre,
            f"{item.cantidad:.2f}",
            f"${item.precio_unitario:.2f}",
            f"${item.descuento:.2f}",
            f"${item.total:.2f}"
        ])
        
    t_items = Table(item_data, colWidths=[20*mm, 75*mm, 15*mm, 25*mm, 20*mm, 25*mm])
    t_items.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.gray),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    elements.append(t_items)
    elements.append(Spacer(1, 5*mm))
    
    # Totales
    totals_data = [
        ["Subtotal:", f"${invoice.subtotal:.2f}"],
        ["Descuentos:", f"-${invoice.descuento_total:.2f}"],
        ["Neto Gravado:", f"${invoice.neto_gravado:.2f}"],
        ["IVA:", f"${invoice.monto_iva:.2f}"],
        ["Total:", f"${invoice.total:.2f}"]
    ]
    t_totals = Table(totals_data, colWidths=[140*mm, 40*mm])
    t_totals.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,-1), (1,-1), 'Helvetica-Bold'),
        ('LINEABOVE', (1,-1), (1,-1), 1, colors.black),
    ]))
    elements.append(t_totals)
    elements.append(Spacer(1, 10*mm))
    
    # Info AFIP (CAE y Vto) - CAE y Codigo Barras si es que existe
    if invoice.cae:
        afip_data = [
            [Paragraph(f"<b>CAE:</b> {invoice.cae}", styleN)],
            [Paragraph(f"<b>Vencimiento CAE:</b> {invoice.cae_vencimiento.strftime('%d/%m/%Y') if invoice.cae_vencimiento else ''}", styleN)]
        ]
        t_afip = Table(afip_data, colWidths=[180*mm])
        t_afip.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ]))
        elements.append(t_afip)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
