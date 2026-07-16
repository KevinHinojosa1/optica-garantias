"""Router envíos masivos WhatsApp."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from schemas.whatsapp_envios import (
    GenerarEnviosRequest,
    GenerarEnviosResponse,
    SubirExcelEnviosResponse,
)
from services.whatsapp_envios_service import PLANTILLA_EJEMPLO, WhatsAppEnviosService
from templates_shared import templates

router = APIRouter(tags=["Envíos WhatsApp"])


@router.get("/envios-whatsapp", response_class=HTMLResponse)
async def pagina_envios_whatsapp(request: Request):
    return templates.TemplateResponse(
        request,
        "whatsapp_envios.html",
        {
            "active": "envios_whatsapp",
            "plantilla_ejemplo": PLANTILLA_EJEMPLO,
        },
    )


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
            asesor=payload.asesor,
            incluir_pie=payload.incluir_pie,
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
            asesor=payload.asesor,
            incluir_pie=payload.incluir_pie,
        )
        xlsx = WhatsAppEnviosService.exportar_excel(data["items"])
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        return Response(
            content=xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="envios_whatsapp_{stamp}.xlsx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc