"""Router reprogramación de entregas — pedidos/órdenes por wa.me y Business API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from schemas.whatsapp_envios import (
    EnviarBusinessLoteRequest,
    EnviarBusinessLoteResponse,
    EnviarBusinessRequest,
    EnviarBusinessResponse,
    GenerarEnviosRequest,
    GenerarEnviosResponse,
    SubirExcelEnviosResponse,
    WhatsAppConfigResponse,
)
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
    }


@router.get("/envios-whatsapp", response_class=HTMLResponse)
async def pagina_envios_whatsapp(request: Request):
    wa_config = WhatsAppBusinessService.info_config()
    return templates.TemplateResponse(
        request,
        "whatsapp_envios.html",
        {
            "active": "envios_whatsapp",
            "plantilla_ejemplo": PLANTILLA_EJEMPLO,
            "wa_business_activa": wa_config["business_api_activa"],
        },
    )


@router.get("/api/envios-whatsapp/config", response_model=WhatsAppConfigResponse)
async def api_config_whatsapp():
    return WhatsAppConfigResponse(**WhatsAppBusinessService.info_config())


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
            payload.plantilla,
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
            payload.plantilla,
            contactos,
            **_kwargs_generar(payload),
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