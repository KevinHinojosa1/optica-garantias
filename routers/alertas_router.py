"""Router Alertas Telegram — módulo integrado en FastAPI."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response

from schemas.alertas import (
    AlertaIngresarRequest,
    AlertaReporteIARequest,
    AlertasClasificarRequest,
    AlertasGuardarRequest,
    AlertasGraficosResponse,
    AlertasKpisResponse,
    AlertasListResponse,
    AlertasSubirExcelResponse,
)
from services.alertas_service import AlertasService
from services.respuesta_ia_service import RespuestaIAService
from templates_shared import templates

router = APIRouter(tags=["Alertas Telegram"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _error_interno(contexto: str, exc: Exception) -> HTTPException:
    logger.exception("%s: %s", contexto, exc)
    return HTTPException(status_code=500, detail=f"{contexto}. Revise los logs del servidor.")


async def _leer_upload(archivo: UploadFile) -> bytes:
    content = await archivo.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB.")
    return content


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

    for nombre, valor in (("fecha_desde", fecha_desde), ("fecha_hasta", fecha_hasta)):
        if valor:
            try:
                date.fromisoformat(valor)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{nombre} debe tener formato AAAA-MM-DD.") from exc

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
def pagina_alertas(request: Request):
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
        raise _error_interno("Error al cargar módulo Alertas", exc) from exc


@router.get("/api/alertas", response_model=AlertasListResponse)
def api_listar_alertas(
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
def api_kpis_alertas(
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
def api_graficos_alertas(
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
def api_guardar_alertas(payload: AlertasGuardarRequest):
    try:
        return AlertasService.guardar_filas(payload.filas)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise _error_interno("Error al guardar", exc) from exc


@router.post("/api/alertas/clasificar-reglas")
def api_clasificar_reglas(payload: AlertasClasificarRequest):
    try:
        return AlertasService.clasificar_reglas(payload.ids)
    except Exception as exc:
        raise _error_interno("Error al clasificar por reglas", exc) from exc


@router.post("/api/alertas/clasificar-ia")
def api_clasificar_ia(payload: AlertasClasificarRequest):
    try:
        return AlertasService.clasificar_ia(payload.ids)
    except Exception as exc:
        raise _error_interno("Error al clasificar con IA", exc) from exc


@router.get("/api/alertas/exportar")
def api_exportar_alertas(
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
def api_recargar_excel():
    try:
        return AlertasService.recargar_excel()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No se encontró el Excel de alertas.") from exc
    except Exception as exc:
        raise _error_interno("Error al recargar Excel", exc) from exc


@router.post("/api/alertas/subir-excel", response_model=AlertasSubirExcelResponse)
async def api_subir_excel_alertas(
    archivo: UploadFile = File(...),
    modo: str = Query("reemplazar", pattern="^(reemplazar|incremental)$"),
):
    nombre = (archivo.filename or "").lower()
    if not nombre.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Suba un archivo Excel (.xlsx) con hoja GENERAL.")
    try:
        content = await _leer_upload(archivo)
        resultado = await run_in_threadpool(AlertasService.subir_excel, content, modo=modo)
        return AlertasSubirExcelResponse(**resultado)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Excel inválido: {exc}") from exc
    except Exception as exc:
        raise _error_interno("Error al procesar Excel", exc) from exc


@router.post("/api/alertas/importar")
async def api_importar_alertas(archivo: UploadFile = File(...)):
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Suba un archivo CSV válido.")
    try:
        content = await _leer_upload(archivo)
        return await run_in_threadpool(AlertasService.importar_csv, content)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise _error_interno("Error al importar", exc) from exc


@router.post("/api/alertas/ingresar")
def api_ingresar_alerta(payload: AlertaIngresarRequest):
    """Crea una nueva alerta manualmente (sin necesidad de subir un Excel)."""
    try:
        resultado = AlertasService.ingresar_alerta(payload.model_dump())
        return resultado
    except Exception as exc:
        raise _error_interno("Error al ingresar alerta", exc) from exc


@router.post("/api/alertas/reporte-ia")
async def api_reporte_ia(payload: AlertaReporteIARequest):
    """Genera un reporte ejecutivo completo con Claude sobre una alerta."""
    try:
        fila: dict = {}
        if payload.alerta_id is not None:
            from centro_operaciones.services.datastore import cargar_alertas
            df = await run_in_threadpool(cargar_alertas)
            rows = df[df["id"] == payload.alerta_id]
            if rows.empty:
                raise HTTPException(status_code=404, detail=f"Alerta {payload.alerta_id} no encontrada.")
            row = rows.iloc[0]
            fila = {col: (str(val) if val is not None and str(val) != 'nan' else '') for col, val in row.items()}
        elif payload.fila:
            fila = payload.fila
        else:
            raise HTTPException(status_code=422, detail="Debe proporcionar alerta_id o fila.")

        resultado = await AlertasService.generar_reporte_ia(
            fila, contexto_extra=payload.contexto_extra or ""
        )
        return resultado
    except HTTPException:
        raise
    except Exception as exc:
        raise _error_interno("Error al generar reporte IA", exc) from exc