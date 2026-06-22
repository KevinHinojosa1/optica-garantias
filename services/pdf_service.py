import io
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import settings
from models.cliente import Cliente
from models.historial import HistorialConsulta
from services.descuento_service import DescuentoService
from services.garantia_service import GarantiaService
from services.tiendas_service import TiendasService

AZUL = colors.HexColor("#1e40af")
AZUL_CLARO = colors.HexColor("#dbeafe")
VERDE = colors.HexColor("#166534")
ROJO = colors.HexColor("#991b1b")
AMARILLO = colors.HexColor("#854d0e")


class PdfService:
    @staticmethod
    def _color_veredicto(veredicto: str):
        v = veredicto.upper()
        if v == "APLICA":
            return VERDE
        if v == "NO APLICA":
            return ROJO
        return AMARILLO

    @classmethod
    def generar_informe_consulta(cls, historial: HistorialConsulta, cliente: Cliente | None) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        styles = getSampleStyleSheet()
        titulo = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=20, textColor=AZUL, spaceAfter=6)
        subtitulo = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey, alignment=TA_CENTER)
        seccion = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=12, textColor=AZUL, spaceBefore=12, spaceAfter=6)
        cuerpo = ParagraphStyle("Cuerpo", parent=styles["Normal"], fontSize=10, leading=14)
        veredicto_style = ParagraphStyle(
            "Veredicto",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=cls._color_veredicto(historial.veredicto),
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=8,
        )

        elementos = []

        # Encabezado
        elementos.append(Paragraph("👓 ÓPTICA LOS ANDES", titulo))
        elementos.append(Paragraph("Informe de Consulta de Garantía", subtitulo))
        elementos.append(Spacer(1, 0.4 * cm))

        fecha_str = historial.created_at.strftime("%d/%m/%Y %H:%M")
        meta = Table(
            [["ID Consulta", f"#{historial.id}"], ["Generado", fecha_str], ["Asesor", historial.asesor]],
            colWidths=[4 * cm, 12 * cm],
        )
        meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), AZUL_CLARO),
                    ("TEXTCOLOR", (0, 0), (0, -1), AZUL),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elementos.append(meta)
        elementos.append(Spacer(1, 0.5 * cm))

        # Veredicto destacado
        elementos.append(Paragraph(f"VEREDICTO IA: {historial.veredicto}", veredicto_style))
        if historial.confianza:
            elementos.append(Paragraph(f"Confianza: {historial.confianza}%", subtitulo))

        # Cliente
        elementos.append(Paragraph("Datos del Cliente", seccion))
        nombre = historial.cliente_nombre
        tienda_nombre = cliente.tienda if cliente else "—"
        tienda_info = TiendasService.resolver_para_cliente(tienda_nombre) if cliente else {}

        filas_cliente = [
            ["Nombre", nombre],
            ["Cédula", cliente.cedula if cliente else "—"],
            ["Teléfono", cliente.telefono if cliente else "—"],
            ["Tienda", tienda_info.get("nombre", tienda_nombre)],
            ["Ciudad", tienda_info.get("ciudad", "—")],
            ["Factura", cliente.numero_factura if cliente else "—"],
            ["Producto", cliente.producto if cliente else "—"],
        ]
        if cliente:
            estado = GarantiaService.evaluar_estado_general(cliente.fecha_factura, cliente.tiene_ola_plus)
            filas_cliente += [
                ["Fecha factura", str(cliente.fecha_factura)],
                ["Estado garantía", estado["estado_garantia"]],
                ["OLA Plus", "Sí" if cliente.tiene_ola_plus else "No"],
            ]

        t_cliente = Table(filas_cliente, colWidths=[4.5 * cm, 11.5 * cm])
        t_cliente.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elementos.append(t_cliente)

        # Descuento
        codigo = historial.codigo_descuento or (cliente.codigo_descuento if cliente else None)
        pct = historial.porcentaje_descuento or (cliente.porcentaje_descuento if cliente else None)
        if codigo or pct:
            elementos.append(Paragraph("Descuento", seccion))
            elementos.append(Paragraph(DescuentoService.texto_reporte(codigo, pct), cuerpo))

        # Análisis
        elementos.append(Paragraph("Análisis de Garantía", seccion))
        if historial.motivo:
            elementos.append(Paragraph(f"<b>Motivo:</b> {historial.motivo}", cuerpo))
        if historial.fundamento:
            elementos.append(Paragraph(f"<b>Fundamento:</b> {historial.fundamento}", cuerpo))

        # Imagen
        if historial.imagen_path:
            img_path = Path(historial.imagen_path)
            if not img_path.is_absolute():
                img_path = Path(settings.base_dir) / img_path
            if img_path.exists():
                elementos.append(Paragraph("Evidencia Fotográfica", seccion))
                try:
                    img = Image(str(img_path), width=14 * cm, height=9 * cm, kind="proportional")
                    elementos.append(img)
                except Exception:
                    elementos.append(Paragraph("(No se pudo cargar la imagen)", cuerpo))

        elementos.append(Spacer(1, 0.8 * cm))
        elementos.append(
            Paragraph(
                f"— Documento generado automáticamente · {settings.app_name} · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                subtitulo,
            )
        )

        doc.build(elementos)
        buffer.seek(0)
        return buffer.getvalue()