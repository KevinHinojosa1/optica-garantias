import os
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from config import LOGO_OFICIAL_PATH, settings
from models.historial import HistorialConsulta
from models.cliente import Cliente
from services.tiendas_service import TiendasService
from services.garantia_service import GarantiaService

class PdfService:
    @classmethod
    def generar_informe_consulta(cls, historial: HistorialConsulta, cliente: Cliente | None) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        elements = []

        # Colors
        teal_color = colors.HexColor('#0D9488')
        light_teal = colors.HexColor('#E6F7F5')
        light_gray = colors.HexColor('#F3F4F6')
        text_color = colors.HexColor('#1E293B')
        white = colors.HexColor('#FFFFFF')

        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=colors.black,
            leading=22
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.gray,
            leading=12
        )

        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=teal_color,
            spaceBefore=12,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=text_color,
            leading=14
        )
        
        bold_body_style = ParagraphStyle(
            'BoldBody',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.black,
            leading=14
        )

        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=text_color,
            leading=14,
            leftIndent=15,
            bulletIndent=5
        )

        teal_bold_center = ParagraphStyle(
            'TealBoldCenter',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=teal_color,
            alignment=1, # Center
            leading=12
        )

        # 1. Header Row
        title_para = Paragraph("INFORME DE REVISIÓN DE LENTES", title_style)
        subtitle_para = Paragraph("Explicación clara para usted", subtitle_style)
        
        logo = None
        if os.path.exists(LOGO_OFICIAL_PATH):
            logo = Image(LOGO_OFICIAL_PATH, width=4*cm, height=1.5*cm)
            logo.hAlign = 'RIGHT'

        header_data = [[
            [title_para, subtitle_para],
            logo if logo else ""
        ]]
        
        header_table = Table(header_data, colWidths=[13*cm, 5*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.8*cm))

        # Date formatting
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        fecha_actual = datetime.now()
        fecha_str = f"{fecha_actual.day} de {meses[fecha_actual.month-1]} de {fecha_actual.year}"

        # 2. Info Table
        # Fallbacks if cliente is None
        orden_trabajo = str(cliente.numero_factura) if cliente and cliente.numero_factura else "N/A"
        
        local_name = "N/A"
        if cliente and cliente.tienda:
            local_name = TiendasService.get_nombre_tienda(cliente.tienda) or cliente.tienda
            
        producto = cliente.producto if cliente and cliente.producto else "Lentes de medida"

        info_data = [
            [
                Paragraph("<b>Orden de trabajo</b>", ParagraphStyle('InfoT', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(orden_trabajo, body_style),
                Paragraph("<b>Local</b>", ParagraphStyle('InfoT', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(local_name, body_style)
            ],
            [
                Paragraph("<b>Fecha</b>", ParagraphStyle('InfoT', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(fecha_str, body_style),
                Paragraph("<b>Producto</b>", ParagraphStyle('InfoT', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(producto, body_style)
            ]
        ]

        info_table = Table(info_data, colWidths=[4*cm, 5*cm, 3*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 1), light_teal),
            ('BACKGROUND', (2, 0), (2, 1), light_teal),
            ('BACKGROUND', (1, 0), (1, 1), white),
            ('BACKGROUND', (3, 0), (3, 1), white),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))

        # 3. Section: ¿Qué revisamos?
        elements.append(Paragraph("¿Qué revisamos?", section_title_style))
        elements.append(Paragraph("Revisamos cuidadosamente sus lentes por ambos lados, sus bordes y las zonas que tocan la montura. El objetivo fue conocer qué ocurrió con la superficie y verificar si el problema podía haberse originado durante la fabricación.", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # 4. Section: ¿Qué encontramos?
        elements.append(Paragraph("¿Qué encontramos?", section_title_style))
        
        motivo_text = historial.motivo if historial.motivo else "Se observan alteraciones en la superficie del lente."
        
        # Determine cause based on veredicto and motivo
        motivo_lower = motivo_text.lower()
        if historial.veredicto == "NO APLICA" and ("craquelado" in motivo_lower or "cuarteado" in motivo_lower):
            cause_text = "Este tipo de daño puede aparecer durante el uso por situaciones como calor intenso, cambios bruscos de temperatura, presión, roce frecuente o productos de limpieza no adecuados para lentes."
        elif historial.veredicto == "NO APLICA" and ("rayado" in motivo_lower or "rayas" in motivo_lower):
            cause_text = "Las rayas pueden aparecer por el uso de materiales abrasivos en la limpieza, contacto con superficies duras o almacenamiento sin protección."
        elif historial.veredicto == "APLICA":
            cause_text = "Este tipo de cambio puede estar relacionado con un defecto en el proceso de fabricación o en los materiales utilizados."
        else:
            cause_text = "Este tipo de cambio puede estar relacionado con diversas situaciones durante el uso o con el proceso de fabricación."

        fab_problem = "Sí, se detectaron señales de un defecto de fabricación." if historial.veredicto == "APLICA" else "No, no encontramos señales de que el problema se haya originado durante la fabricación."
        if historial.veredicto == "IMAGEN NO CLARA":
            fab_problem = "No es posible determinar con la información actual. Se requiere una revisión presencial."

        encontramos_data = [
            [
                Paragraph("<b>¿Qué observamos?</b>", ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(motivo_text, body_style)
            ],
            [
                Paragraph("<b>¿Qué puede causar este tipo de cambio?</b>", ParagraphStyle('T2', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(cause_text, body_style)
            ],
            [
                Paragraph("<b>¿Encontramos un problema de fabricación?</b>", ParagraphStyle('T3', fontName='Helvetica-Bold', fontSize=10, textColor=teal_color)),
                Paragraph(fab_problem, body_style)
            ]
        ]

        encontramos_table = Table(encontramos_data, colWidths=[6*cm, 12*cm])
        encontramos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), light_teal),
            ('BACKGROUND', (1, 0), (1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(encontramos_table)
        elements.append(Spacer(1, 0.5*cm))

        # 5. Section: ¿Cuál es el resultado de la revisión?
        elements.append(Paragraph("¿Cuál es el resultado de la revisión?", section_title_style))
        
        fundamento_text = historial.fundamento if historial.fundamento else "Se ha revisado según nuestras políticas de garantía."
        resultado_combinado = f"{motivo_text} {fundamento_text}"
        
        resultado_data = [[Paragraph(resultado_combinado, bold_body_style)]]
        resultado_table = Table(resultado_data, colWidths=[18*cm])
        resultado_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), light_gray),
            ('TOPPADDING', (0, 0), (0, 0), 10),
            ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ('LEFTPADDING', (0, 0), (0, 0), 10),
            ('RIGHTPADDING', (0, 0), (0, 0), 10),
        ]))
        elements.append(resultado_table)
        elements.append(Spacer(1, 0.5*cm))

        # 6. Warranty Decision Line
        if historial.veredicto == "APLICA":
            decision_text = "En esta ocasión la garantía sí aplica, porque en la revisión encontramos señales de que el problema se originó durante la fabricación."
        elif historial.veredicto == "NO APLICA":
            decision_text = "En esta ocasión no aplica, porque en la revisión no encontramos señales de que el problema se haya originado durante la fabricación."
        else:
            decision_text = "No es posible determinar con la información actual. Se requiere una revisión presencial."
            
        elements.append(Paragraph(f"<b>¿La garantía aplica en este caso?</b> {decision_text}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # 7. Section: ¿Cómo puede cuidar mejor sus lentes?
        elements.append(Paragraph("¿Cómo puede cuidar mejor sus lentes?", section_title_style))
        
        bullets = [
            "<b>Para limpiarlos:</b> use un paño de microfibra limpio y un producto adecuado para lentes. Evite limpiadores del hogar o productos químicos fuertes.",
            "<b>Para protegerlos del calor:</b> no los deje dentro del vehículo expuestos al sol ni cerca de fuentes de calor.",
            "<b>Evite cambios bruscos de temperatura:</b> por ejemplo, no exponga los lentes inmediatamente a calor intenso después de haber estado en un ambiente muy frío.",
            "<b>Para evitar presión y roce:</b> no los coloque con los lentes hacia abajo ni debajo de objetos pesados.",
            "<b>Cuando no los use:</b> guárdelos en su estuche para protegerlos."
        ]
        
        for bullet in bullets:
            elements.append(Paragraph(f"• {bullet}", bullet_style))
        
        elements.append(Spacer(1, 0.5*cm))

        # 8. Commitment Block
        compromiso_text = "<b>Nuestro compromiso con usted:</b> queremos que conozca de forma clara qué observamos, por qué llegamos a este resultado y cómo puede cuidar mejor sus lentes. Si tiene alguna duda sobre esta revisión, nuestro equipo de Servicio al Cliente está disponible para orientarlo."
        
        compromiso_data = [[Paragraph(compromiso_text, ParagraphStyle('Compromiso', parent=body_style, textColor=teal_color))]]
        compromiso_table = Table(compromiso_data, colWidths=[18*cm])
        compromiso_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), light_teal),
            ('TOPPADDING', (0, 0), (0, 0), 10),
            ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ('LEFTPADDING', (0, 0), (0, 0), 10),
            ('RIGHTPADDING', (0, 0), (0, 0), 10),
        ]))
        elements.append(compromiso_table)
        elements.append(Spacer(1, 1.5*cm))

        # 9. Signature Block
        signature_left = [
            Paragraph("________________________", teal_bold_center),
            Paragraph("SERVICIO AL CLIENTE / POSVENTA", teal_bold_center),
            Paragraph("ÓPTICA LOS ANDES S.A.", teal_bold_center)
        ]
        
        signature_right = [
            Paragraph("________________________", teal_bold_center),
            Paragraph("RESPONSABLE DE REVISIÓN / AUTORIZACIÓN", teal_bold_center),
            Paragraph("ÓPTICA LOS ANDES S.A.", teal_bold_center)
        ]
        
        signature_data = [[signature_left, signature_right]]
        signature_table = Table(signature_data, colWidths=[9*cm, 9*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(signature_table)

        # Build PDF
        doc.build(elements)
        return buffer.getvalue()