from fastapi import APIRouter, HTTPException, Query

from schemas.respuesta_ia import (
    GenerarRespuestaIARequest,
    GenerarRespuestaIAResponse,
    GuardarPlantillaRequest,
    PlantillaRespuestaIA,
    PlantillasListResponse,
    RespuestasRapidasResponse,
)
from services.respuesta_ia_service import RespuestaIAService

router = APIRouter(tags=["IA — Respuesta reutilizable"])


@router.get("/api/ia/disponible")
async def ia_disponible():
    return RespuestaIAService.ia_disponible()


@router.post("/api/ia/generar-respuesta", response_model=GenerarRespuestaIAResponse)
async def generar_respuesta(payload: GenerarRespuestaIARequest):
    try:
        ctx = payload.contexto.model_dump()
        resultado = await RespuestaIAService.generar(
            ctx,
            titulo_modulo=payload.titulo_modulo,
            guardar_como_plantilla=payload.guardar_como_plantilla,
            nombre_plantilla=payload.nombre_plantilla,
        )
        return GenerarRespuestaIAResponse(**resultado)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta IA: {exc}") from exc


@router.post("/api/ia/respuestas-rapidas", response_model=RespuestasRapidasResponse)
async def respuestas_rapidas(payload: GenerarRespuestaIARequest):
    """Bot de respuesta rápida: 3 tonos (empática, corta, formal) listos para WhatsApp."""
    try:
        ctx = payload.contexto.model_dump()
        resultado = await RespuestaIAService.generar_respuestas_rapidas(
            ctx,
            titulo_modulo=payload.titulo_modulo or "Alertas Telegram",
        )
        return RespuestasRapidasResponse(**resultado)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error bot de respuestas: {exc}") from exc


@router.get("/api/ia/plantillas", response_model=PlantillasListResponse)
async def listar_plantillas(modulo: str = Query("")):
    items = RespuestaIAService.listar_plantillas(modulo)
    return PlantillasListResponse(plantillas=[PlantillaRespuestaIA(**p) for p in items])


@router.post("/api/ia/plantillas", response_model=PlantillaRespuestaIA)
async def guardar_plantilla(payload: GuardarPlantillaRequest):
    try:
        entry = RespuestaIAService.guardar_plantilla(
            nombre=payload.nombre,
            modulo=payload.modulo,
            mensaje_whatsapp=payload.mensaje_whatsapp,
            mensaje_correo=payload.mensaje_correo,
            asunto_correo=payload.asunto_correo,
            metadata=payload.metadata,
        )
        return PlantillaRespuestaIA(**entry)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc