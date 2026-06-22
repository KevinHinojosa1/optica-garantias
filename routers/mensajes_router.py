from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.cliente import Cliente
from routers.clientes_router import cliente_to_response
from services.historial_service import HistorialService
from services.whatsapp_service import WhatsAppService

router = APIRouter(tags=["Módulo 4 - Mensajes"])


class MensajeRequest(BaseModel):
    cliente_id: int
    mensaje: str | None = None
    analisis: dict | None = None
    asesor: str | None = None
    historial_id: int | None = None
    incluir_pdf: bool = False


class MensajePdfRequest(BaseModel):
    cliente_id: int
    historial_id: int
    mensaje: str | None = None


class MensajeResponse(BaseModel):
    mensaje: str
    wa_link: str
    tienda: str
    grupo_nombre: str
    veredicto: str | None = None
    pdf_url: str | None = None


def _url_pdf(request: Request, historial_id: int) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/historial/{historial_id}/pdf"


@router.post("/api/mensajes/generar", response_model=MensajeResponse)
async def generar_mensaje(
    payload: MensajeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == payload.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    try:
        data = cliente_to_response(cliente).model_dump(mode="json")

        asesor = payload.asesor or ""

        analisis = payload.analisis
        veredicto = None

        if payload.mensaje:
            mensaje = payload.mensaje
        elif analisis:
            veredicto = analisis.get("veredicto", "")
            mensaje = WhatsAppService.generar_desde_analisis(data, analisis, asesor)
        else:
            ultimo = HistorialService.ultimo_por_cliente(db, payload.cliente_id)
            if ultimo:
                analisis = {
                    "veredicto": ultimo.veredicto,
                    "motivo": ultimo.motivo or "",
                    "fundamento": ultimo.fundamento or "",
                    "confianza": ultimo.confianza or 0,
                }
                veredicto = ultimo.veredicto
                mensaje = WhatsAppService.generar_desde_analisis(data, analisis, asesor)
            else:
                mensaje = WhatsAppService.mensaje_pre_cargado(data, asesor)

        pdf_url = None
        historial_id = payload.historial_id
        if payload.incluir_pdf:
            if not historial_id:
                ultimo = HistorialService.ultimo_por_cliente(db, payload.cliente_id)
                historial_id = ultimo.id if ultimo else None
            if historial_id:
                pdf_url = _url_pdf(request, historial_id)
                mensaje = WhatsAppService.agregar_enlace_pdf(mensaje, pdf_url, historial_id)

        wa_link, tienda = WhatsAppService.enlace_grupo_apoyo(data, mensaje)

        if analisis and not payload.mensaje:
            ultimo = HistorialService.ultimo_por_cliente(db, payload.cliente_id)
            if ultimo:
                HistorialService.actualizar_mensaje(db, ultimo.id, mensaje)

        return MensajeResponse(
            mensaje=mensaje,
            wa_link=wa_link,
            tienda=tienda.get("nombre", ""),
            grupo_nombre=tienda.get("whatsapp_grupo_nombre", "Grupo de Apoyo"),
            veredicto=veredicto,
            pdf_url=pdf_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar mensaje: {exc}") from exc


@router.post("/api/mensajes/whatsapp-pdf", response_model=MensajeResponse)
async def mensaje_whatsapp_con_pdf(
    payload: MensajePdfRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == payload.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    registro = HistorialService.obtener(db, payload.historial_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Consulta de historial no encontrada.")
    if registro.cliente_id and registro.cliente_id != payload.cliente_id:
        raise HTTPException(status_code=422, detail="La consulta no pertenece a este cliente.")

    try:
        data = cliente_to_response(cliente).model_dump(mode="json")
        mensaje_base = payload.mensaje.strip() if payload.mensaje else (registro.mensaje_enviado or "")
        if not mensaje_base:
            analisis = {
                "veredicto": registro.veredicto,
                "motivo": registro.motivo or "",
                "fundamento": registro.fundamento or "",
                "confianza": registro.confianza or 0,
            }
            mensaje_base = WhatsAppService.generar_desde_analisis(data, analisis, registro.asesor)

        pdf_url = _url_pdf(request, payload.historial_id)
        mensaje = WhatsAppService.agregar_enlace_pdf(mensaje_base, pdf_url, payload.historial_id)
        wa_link, tienda = WhatsAppService.enlace_grupo_apoyo(data, mensaje)

        return MensajeResponse(
            mensaje=mensaje,
            wa_link=wa_link,
            tienda=tienda.get("nombre", ""),
            grupo_nombre=tienda.get("whatsapp_grupo_nombre", "Grupo de Apoyo"),
            veredicto=registro.veredicto,
            pdf_url=pdf_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al preparar mensaje con PDF: {exc}") from exc