import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from schemas.scripts import (
    ArmarWhatsAppRequest,
    ArmarWhatsAppResponse,
    BuscarFuentesResponse,
    FichaCliente,
    GenerarRespuestaRequest,
    GenerarRespuestaResponse,
)
from services.scripts_ai_service import ScriptsAiService
from services.scripts_service import ScriptsService
from services.tiendas_service import TiendasService

router = APIRouter(tags=["Módulo 7 - Scripts"])
templates = Jinja2Templates(directory="templates")


@router.get("/scripts", response_class=HTMLResponse)
async def pagina_scripts(request: Request):
    tiendas = [t for t in TiendasService.listar() if t["id"] != "central-call-center"]
    return templates.TemplateResponse(
        request,
        "scripts.html",
        {
            "active": "scripts",
            "tiendas_json": json.dumps(tiendas),
        },
    )


@router.get("/api/scripts")
async def api_scripts():
    try:
        return ScriptsService.cargar()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al cargar scripts: {exc}") from exc


@router.get("/api/scripts/buscar", response_model=BuscarFuentesResponse)
async def buscar_fuentes(
    q: str = Query("", min_length=0),
    db: Session = Depends(get_db),
):
    try:
        resultados = ScriptsService.buscar_fuentes(db, q)
        return BuscarFuentesResponse(resultados=resultados)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al buscar: {exc}") from exc


@router.get("/api/scripts/ficha/atencion/{cliente_id}", response_model=FichaCliente)
async def ficha_atencion(cliente_id: int, db: Session = Depends(get_db)):
    ficha = ScriptsService.ficha_desde_cliente(db, cliente_id)
    if not ficha:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return ficha


@router.get("/api/scripts/ficha/historial/{historial_id}", response_model=FichaCliente)
async def ficha_historial(historial_id: int, db: Session = Depends(get_db)):
    ficha = ScriptsService.ficha_desde_historial(db, historial_id)
    if not ficha:
        raise HTTPException(status_code=404, detail="Consulta de historial no encontrada.")
    return ficha


@router.post("/api/scripts/armar-whatsapp", response_model=ArmarWhatsAppResponse)
async def armar_whatsapp(payload: ArmarWhatsAppRequest):
    try:
        ficha = payload.ficha.model_dump()
        cuerpo = ScriptsService.extraer_cuerpo_whatsapp(payload.cuerpo)
        resultado = ScriptsService.armar_whatsapp(cuerpo, ficha, payload.asesor)
        return ArmarWhatsAppResponse(
            mensaje=resultado["mensaje"],
            wa_link=resultado["wa_link"],
            incluye_ficha=resultado.get("incluye_ficha", False),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al armar WhatsApp: {exc}") from exc


@router.post("/api/scripts/generar-respuesta", response_model=GenerarRespuestaResponse)
async def generar_respuesta(payload: GenerarRespuestaRequest):
    try:
        ficha = payload.ficha.model_dump()
        resultado = await ScriptsAiService.generar_respuesta(
            mensaje_cliente=payload.mensaje_cliente,
            ficha=ficha,
            asesor=payload.asesor,
            escenario=payload.escenario,
            contexto_adicional=payload.contexto_adicional,
        )
        return GenerarRespuestaResponse(**resultado)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta: {exc}") from exc


@router.get("/api/scripts/exportar")
async def exportar_scripts():
    try:
        content = ScriptsService.exportar_excel()
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=scripts_atencion_cliente.xlsx"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al exportar scripts: {exc}") from exc