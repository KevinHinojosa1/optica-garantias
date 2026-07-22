"""Router reprogramación de entregas — cliente, tienda, correo y contador diario."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from schemas.whatsapp_envios import (
    EnviarBusinessLoteRequest,
    EnviarBusinessLoteResponse,
    EnviarBusinessRequest,
    EnviarBusinessResponse,
    EnviarCorreoRequest,
    GenerarEnviosRequest,
    GenerarEnviosResponse,
    MarcarEnviadoRequest,
    SubirExcelEnviosResponse,
    WhatsAppConfigResponse,
)
from services.email_service import EmailService
from services.reprogramacion_log_service import ReprogramacionLogService
from services.whatsapp_business_service import WhatsAppBusinessService
from services.whatsapp_envios_service import PLANTILLA_EJEMPLO, WhatsAppEnviosService
from templates_shared import templates

router = APIRouter(tags=["Reprogramación de entregas"])


def _kwargs_generar(payload: GenerarEnviosRequest) -> dict:
    return {
        "asesor": payload.asesor,
        "incluir_pie": payload.incluir_pie,
        "fecha_reprogramada": payload.fecha_reprogramada,
        "fecha_anterior": payload.fecha_anterior,
        "hora": payload.hora,
        "motivo": payload.motivo,
        "registrar_log": payload.registrar_log,
    }


def _db_info() -> dict:
    url = settings.database_url or ""
    if url.startswith("sqlite"):
        motor = "SQLite"
        detalle = url.replace("sqlite:///", "")
    elif "postgres" in url:
        motor = "PostgreSQL"
        detalle = "conectado (producción)"
    else:
        motor = "SQLAlchemy"
        detalle = url[:40] + ("…" if len(url) > 40 else "")
    return {"motor": motor, "detalle": detalle, "fuente": "base_de_datos"}


@router.get("/envios-whatsapp", response_class=HTMLResponse)
async def pagina_envios_whatsapp(request: Request, db: Session = Depends(get_db)):
    wa_config = WhatsAppBusinessService.info_config()
    mail_config = EmailService.info_config()
    resumen = ReprogramacionLogService.resumen_dia(db=db)
    return templates.TemplateResponse(
        request,
        "whatsapp_envios.html",
        {
            "active": "envios_whatsapp",
            "plantilla_ejemplo": PLANTILLA_EJEMPLO,
            "wa_business_activa": wa_config["business_api_activa"],
            "smtp_activo": mail_config["smtp_activo"],
            "resumen_dia": resumen,
            "db_info": _db_info(),
        },
    )


@router.get("/api/envios-whatsapp/config", response_model=WhatsAppConfigResponse)
async def api_config_whatsapp():
    wa = WhatsAppBusinessService.info_config()
    mail = EmailService.info_config()
    return WhatsAppConfigResponse(
        business_api_activa=wa["business_api_activa"],
        phone_number_id=wa.get("phone_number_id", ""),
        api_version=wa.get("api_version", ""),
        smtp_activo=mail["smtp_activo"],
        smtp_host=mail.get("smtp_host", ""),
        smtp_from=mail.get("smtp_from", ""),
    )


@router.get("/api/envios-whatsapp/resumen-dia")
async def api_resumen_dia(fecha: str | None = None, db: Session = Depends(get_db)):
    return ReprogramacionLogService.resumen_dia(fecha, db=db)


@router.get("/api/envios-whatsapp/historial")
async def api_historial_reprogramaciones(
    fecha: str | None = None,
    local: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    data = ReprogramacionLogService.listar(fecha=fecha, local=local, limit=limit, db=db)
    data["db"] = _db_info()
    return data


@router.post("/api/envios-whatsapp/subir-excel", response_model=SubirExcelEnviosResponse)
async def api_subir_excel_envios(archivo: UploadFile = File(...)):
    if not archivo.filename:
        raise HTTPException(status_code=400, detail="Seleccione un archivo.")
    try:
        content = await archivo.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")
        data = WhatsAppEnviosService.parsear_excel(content, archivo.filename)
        return SubirExcelEnviosResponse(**data)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al leer Excel: {exc}") from exc


@router.post("/api/envios-whatsapp/generar", response_model=GenerarEnviosResponse)
async def api_generar_envios(payload: GenerarEnviosRequest):
    try:
        contactos = [c.model_dump() for c in payload.contactos]
        data = WhatsAppEnviosService.generar_lote(
            payload.plantilla or PLANTILLA_EJEMPLO,
            contactos,
            **_kwargs_generar(payload),
        )
        return GenerarEnviosResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/envios-whatsapp/exportar")
async def api_exportar_envios(payload: GenerarEnviosRequest):
    try:
        contactos = [c.model_dump() for c in payload.contactos]
        data = WhatsAppEnviosService.generar_lote(
            payload.plantilla or PLANTILLA_EJEMPLO,
            contactos,
            **{**_kwargs_generar(payload), "registrar_log": False},
        )
        xlsx = WhatsAppEnviosService.exportar_excel(data["items"])
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        return Response(
            content=xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="entregas_reprogramadas_{stamp}.xlsx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/envios-whatsapp/marcar-enviado")
async def api_marcar_enviado(payload: MarcarEnviadoRequest, db: Session = Depends(get_db)):
    resumen = ReprogramacionLogService.registrar_envio(
        local=payload.local,
        nombre=payload.nombre,
        producto=payload.producto,
        factura=payload.factura,
        telefono=payload.telefono,
        canal=payload.canal,
        estado=payload.estado,
        db=db,
    )
    return {
        "ok": True,
        "resumen_local": resumen,
        "resumen_dia": ReprogramacionLogService.resumen_dia(db=db),
        "db": _db_info(),
    }


@router.post("/api/envios-whatsapp/enviar-correo")
async def api_enviar_correo(payload: EnviarCorreoRequest):
    if not payload.email_tienda.strip():
        raise HTTPException(
            status_code=400,
            detail="Indique el correo de la tienda (columna email_tienda en el Excel o campo del formulario).",
        )
    try:
        if EmailService.esta_configurado():
            result = EmailService.enviar(
                destinatario=payload.email_tienda,
                asunto=payload.asunto,
                cuerpo=payload.cuerpo,
            )
            return {"ok": True, "modo": "smtp", **result}

        mailto = EmailService.mailto_link(payload.email_tienda, payload.asunto, payload.cuerpo)
        return {
            "ok": True,
            "modo": "mailto",
            "mailto": mailto,
            "mensaje": "SMTP no configurado — use el enlace mailto o copie el correo.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/envios-whatsapp/enviar-business", response_model=EnviarBusinessResponse)
async def api_enviar_business(payload: EnviarBusinessRequest):
    if not WhatsAppBusinessService.esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="WhatsApp Business API no configurada. Agregue WHATSAPP_BUSINESS_TOKEN y WHATSAPP_PHONE_NUMBER_ID.",
        )
    item = payload.item
    try:
        result = WhatsAppBusinessService.enviar_texto(item.telefono_limpio, item.mensaje)
        return EnviarBusinessResponse(
            ok=True,
            message_id=result.get("message_id", ""),
            telefono=result.get("telefono", item.telefono_limpio),
            indice=item.indice,
        )
    except ValueError as exc:
        return EnviarBusinessResponse(ok=False, indice=item.indice, error=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/envios-whatsapp/enviar-business-lote", response_model=EnviarBusinessLoteResponse)
async def api_enviar_business_lote(payload: EnviarBusinessLoteRequest):
    if not WhatsAppBusinessService.esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="WhatsApp Business API no configurada. Agregue WHATSAPP_BUSINESS_TOKEN y WHATSAPP_PHONE_NUMBER_ID.",
        )
    items = [i.model_dump() for i in payload.items]
    try:
        data = WhatsAppBusinessService.enviar_lote(items)
        return EnviarBusinessLoteResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
