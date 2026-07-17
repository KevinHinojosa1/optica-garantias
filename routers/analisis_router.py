from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.cliente import Cliente
from routers.clientes_router import cliente_to_response
from schemas.historial import HistorialCreate
from services.descuento_service import DescuentoService
from services.historial_service import HistorialService
from services.conocimiento_service import ConocimientoService
from services.vision_service import VisionService
from services.whatsapp_service import WhatsAppService

router = APIRouter(tags=["Módulo 3 - Análisis"])


def _extension_mime(mime_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    return mapping.get(mime_type, ".jpg")


def _guardar_imagen(historial_id: int, image_bytes: bytes, mime_type: str) -> str:
    directorio = settings.base_dir / settings.consultas_imagenes_dir
    directorio.mkdir(parents=True, exist_ok=True)
    ext = _extension_mime(mime_type)
    ruta = directorio / f"consulta_{historial_id}{ext}"
    ruta.write_bytes(image_bytes)
    return str(Path(settings.consultas_imagenes_dir) / ruta.name)


@router.post("/api/analizar/{cliente_id}")
async def analizar_dano(
    cliente_id: int,
    imagen: UploadFile = File(...),
    asesor: str = Form(default=None),
    codigo_descuento: str = Form(default=""),
    porcentaje_descuento: str = Form(default=""),
    modo_analisis: str = Form(default="conocimiento"),
    db: Session = Depends(get_db),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG, PNG, WEBP).")

    modo = (modo_analisis or "conocimiento").strip().lower()
    if modo not in ("conocimiento", "claude_total"):
        modo = "conocimiento"

    try:
        image_bytes = await imagen.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="La imagen está vacía.")

        codigo_int = int(codigo_descuento) if codigo_descuento.strip() else cliente.codigo_descuento
        pct_int = int(porcentaje_descuento) if porcentaje_descuento.strip() else cliente.porcentaje_descuento
        codigo_int, pct_int = DescuentoService.validar(codigo_int, pct_int)
        cliente.codigo_descuento = codigo_int
        cliente.porcentaje_descuento = pct_int
        db.commit()
        db.refresh(cliente)

        cliente_data = cliente_to_response(cliente).model_dump(mode="json")
        asesor_final = (asesor or "").strip() or settings.default_asesor

        conocimiento = None
        if modo == "conocimiento":
            ConocimientoService.sembrar_inicial(db)
            conocimiento = ConocimientoService.buscar_relevantes(db, cliente_data)

        analisis = await VisionService.analizar_imagen(
            image_bytes,
            imagen.content_type,
            cliente_data,
            conocimiento=conocimiento,
        )
        analisis["modo_analisis"] = modo
        if modo == "claude_total":
            analisis["potenciado_por"] = "Claude total"
            analisis["fuentes_conocimiento"] = []
        elif analisis.get("potenciado_por") == "Claude":
            analisis["potenciado_por"] = "Claude + Base de conocimiento"

        mensaje = WhatsAppService.generar_desde_analisis(cliente_data, analisis, asesor_final)
        wa_link, tienda = WhatsAppService.enlace_grupo_apoyo(cliente_data, mensaje)

        registro = HistorialService.registrar(
            db,
            HistorialCreate(
                cliente_id=cliente.id,
                cliente_nombre=cliente.nombre,
                veredicto=analisis.get("veredicto", "IMAGEN NO CLARA"),
                motivo=analisis.get("motivo"),
                fundamento=analisis.get("fundamento"),
                confianza=analisis.get("confianza"),
                asesor=asesor_final,
                mensaje_enviado=mensaje,
                codigo_descuento=codigo_int,
                porcentaje_descuento=pct_int,
            ),
        )

        imagen_rel = _guardar_imagen(registro.id, image_bytes, imagen.content_type)
        HistorialService.actualizar_imagen(db, registro.id, imagen_rel)

        return {
            "cliente": cliente_data,
            "analisis": analisis,
            "mensaje": mensaje,
            "wa_link": wa_link,
            "grupo_nombre": tienda.get("whatsapp_grupo_nombre", "Grupo de Apoyo"),
            "historial_id": registro.id,
            "pdf_url": f"/api/historial/{registro.id}/pdf",
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en análisis de imagen: {exc}") from exc