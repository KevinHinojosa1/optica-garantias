"""Router Alertas Telegram — módulo integrado en FastAPI."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from schemas.alertas import (
    AlertasClasificarRequest,
    AlertasGuardarRequest,
    AlertasGraficosResponse,
    AlertasKpisResponse,
    AlertasListResponse,
)
from services.alertas_service import AlertasService
from services.respuesta_ia_service import RespuestaIAService
from templates_shared import templates

router = APIRouter(tags=["Alertas Telegram"])


def _filtros_desde_query(
    *,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    locales: Optional[str] = None,
    areas: Optional[str] = None,
    clasificaciones: Optional[str] = None,
    estados: Optional[str] = None,
    contesto: Optional[str] = None,
    texto: str = "",
    solo_pendientes: bool = False,
    meses: Optional[str] = None,
) -> dict:
    def split_csv(val: Optional[str]) -> list[str]:
        if not val:
            return []
        return [x.strip() for x in val.split(",") if x.strip()]

    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "locales": split_csv(locales),
        "areas": split_csv(areas),
        "clasificaciones": split_csv(clasificaciones),
        "estados": split_csv(estados),
        "contesto": split_csv(contesto),
        "texto": texto,
        "solo_pendientes": solo_pendientes,
        "meses": split_csv(meses),
    }


@router.get("/alertas", response_class=HTMLResponse)
async def pagina_alertas(request: Request):
    try:
        meta = AlertasService.metadata()
        ia = RespuestaIAService.ia_disponible()
        return templates.TemplateResponse(
            request,
            "alertas.html",
            {
                "active": "alertas",
                "meta": meta,
                "ia_disponible": ia["disponible"],
                "ia_modelo": ia["modelo"],
            },
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar módulo Alertas: {exc}",
        ) from exc


@router.get("/api/alertas", response_model=AlertasListResponse)
async def api_listar_alertas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    locales: Optional[str] = None,
    areas: Optional[str] = None,
    clasificaciones: Optional[str] = None,
    estados: Optional[str] = None,
    contesto: Optional[str] = None,
    texto: str = "",
    solo_pendientes: bool = False,
    meses: Optional[str] = None,
):
    filtros = _filtros_desde_query(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=locales,
        areas=areas,
        clasificaciones=clasificaciones,
        estados=estados,
        contesto=contesto,
        texto=texto,
        solo_pendientes=solo_pendientes,
        meses=meses,
    )
    return AlertasListResponse(**AlertasService.listar(filtros))


@router.get("/api/alertas/kpis", response_model=AlertasKpisResponse)
async def api_kpis_alertas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    locales: Optional[str] = None,
    areas: Optional[str] = None,
    clasificaciones: Optional[str] = None,
    estados: Optional[str] = None,
    contesto: Optional[str] = None,
    texto: str = "",
    solo_pendientes: bool = False,
    meses: Optional[str] = None,
):
    filtros = _filtros_desde_query(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=locales,
        areas=areas,
        clasificaciones=clasificaciones,
        estados=estados,
        contesto=contesto,
        texto=texto,
        solo_pendientes=solo_pendientes,
        meses=meses,
    )
    return AlertasKpisResponse(**AlertasService.kpis(filtros))


@router.get("/api/alertas/graficos", response_model=AlertasGraficosResponse)
async def api_graficos_alertas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    locales: Optional[str] = None,
    areas: Optional[str] = None,
    clasificaciones: Optional[str] = None,
    estados: Optional[str] = None,
    contesto: Optional[str] = None,
    texto: str = "",
    solo_pendientes: bool = False,
    meses: Optional[str] = None,
):
    filtros = _filtros_desde_query(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=locales,
        areas=areas,
        clasificaciones=clasificaciones,
        estados=estados,
        contesto=contesto,
        texto=texto,
        solo_pendientes=solo_pendientes,
        meses=meses,
    )
    return AlertasGraficosResponse(**AlertasService.graficos(filtros))


@router.post("/api/alertas/guardar")
async def api_guardar_alertas(payload: AlertasGuardarRequest):
    try:
        return AlertasService.guardar_filas(payload.filas)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {exc}") from exc


@router.post("/api/alertas/clasificar-reglas")
async def api_clasificar_reglas(payload: AlertasClasificarRequest):
    try:
        return AlertasService.clasificar_reglas(payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/alertas/clasificar-ia")
async def api_clasificar_ia(payload: AlertasClasificarRequest):
    try:
        return AlertasService.clasificar_ia(payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/alertas/exportar")
async def api_exportar_alertas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    locales: Optional[str] = None,
    areas: Optional[str] = None,
    clasificaciones: Optional[str] = None,
    estados: Optional[str] = None,
    contesto: Optional[str] = None,
    texto: str = "",
    solo_pendientes: bool = False,
    meses: Optional[str] = None,
):
    filtros = _filtros_desde_query(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        locales=locales,
        areas=areas,
        clasificaciones=clasificaciones,
        estados=estados,
        contesto=contesto,
        texto=texto,
        solo_pendientes=solo_pendientes,
        meses=meses,
    )
    data = AlertasService.exportar_excel(filtros)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="matriz_seguimiento_alertas_{stamp}.xlsx"'},
    )


@router.post("/api/alertas/recargar-excel")
async def api_recargar_excel():
    try:
        return AlertasService.recargar_excel()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/alertas/importar")
async def api_importar_alertas(archivo: UploadFile = File(...)):
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Suba un archivo CSV válido.")
    try:
        content = await archivo.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")
        return AlertasService.importar_csv(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al importar: {exc}") from exc