import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from schemas.ivr import IvrActualizarRequest, IvrRegistroRequest, IvrRegistroResponse, IvrTiendaEstado
from services.google_sheets_service import GoogleSheetsService
from services.ivr_service import IvrService
from services.tiendas_service import TiendasService

router = APIRouter(tags=["Módulo 6 - IVR"])
templates = Jinja2Templates(directory="templates")


@router.get("/ivr", response_class=HTMLResponse)
async def pagina_ivr(request: Request):
    tiendas = TiendasService.listar_ivr()
    ciudades = sorted({t["ciudad"] for t in tiendas})
    dia_hoy = TiendasService.dia_ivr_laboral(date.today())
    nombres_dia = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}
    conteo_dia = {d: sum(1 for t in tiendas if t.get("dia_ivr") == d) for d in range(1, 6)}
    return templates.TemplateResponse(
        request,
        "ivr.html",
        {
            "active": "ivr",
            "tiendas_json": json.dumps(tiendas),
            "ciudades": ciudades,
            "google_sheets_activo": GoogleSheetsService.configurado(),
            "semana_actual": IvrService.semana_iso(),
            "dia_hoy": dia_hoy,
            "nombre_dia_hoy": nombres_dia.get(dia_hoy, ""),
            "total_tiendas": len(tiendas),
            "conteo_dia": conteo_dia,
        },
    )


@router.get("/api/ivr/estado", response_model=list[IvrTiendaEstado])
async def estado_ivr(
    semana: str = Query("", description="Semana ISO ej: 2026-W25"),
    db: Session = Depends(get_db),
):
    try:
        sem = semana.strip() or None
        return IvrService.resumen_semana(db, sem)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al cargar estado IVR: {exc}") from exc


@router.post("/api/ivr/registrar", response_model=IvrRegistroResponse)
async def registrar_ivr(payload: IvrRegistroRequest, db: Session = Depends(get_db)):
    try:
        resultado = IvrService.registrar(
            db,
            tienda_id=payload.tienda_id,
            funciona=payload.funciona,
            comentario=payload.comentario,
            verificado_por=payload.verificado_por,
        )
        reg = resultado["registro"]
        sheets = resultado["google_sheets"]
        return IvrRegistroResponse(
            id=reg.id,
            tienda_id=reg.tienda_id,
            tienda_nombre=reg.tienda_nombre,
            ciudad=reg.ciudad,
            funciona=reg.funciona,
            comentario=reg.comentario,
            verificado_por=reg.verificado_por,
            fecha=reg.fecha.isoformat(),
            semana=reg.semana,
            created_at=reg.created_at,
            google_sheets_ok=sheets.get("ok", False),
            google_sheets_mensaje=sheets.get("motivo", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar IVR: {exc}") from exc


@router.get("/api/ivr/historial")
async def historial_ivr(db: Session = Depends(get_db), limit: int = 50):
    try:
        registros = IvrService.listar_recientes(db, limit=limit)
        return [
            {
                "id": r.id,
                "tienda_id": r.tienda_id,
                "tienda_nombre": r.tienda_nombre,
                "ciudad": r.ciudad,
                "funciona": r.funciona,
                "comentario": r.comentario,
                "verificado_por": r.verificado_por,
                "fecha": r.fecha.isoformat(),
                "semana": r.semana,
                "created_at": r.created_at.isoformat(),
            }
            for r in registros
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al cargar historial IVR: {exc}") from exc


@router.patch("/api/ivr/{registro_id}", response_model=IvrRegistroResponse)
async def actualizar_ivr(
    registro_id: int,
    payload: IvrActualizarRequest,
    db: Session = Depends(get_db),
):
    try:
        reg = IvrService.actualizar(
            db,
            registro_id,
            funciona=payload.funciona,
            comentario=payload.comentario,
            verificado_por=payload.verificado_por,
        )
        return IvrRegistroResponse(
            id=reg.id,
            tienda_id=reg.tienda_id,
            tienda_nombre=reg.tienda_nombre,
            ciudad=reg.ciudad,
            funciona=reg.funciona,
            comentario=reg.comentario,
            verificado_por=reg.verificado_por,
            fecha=reg.fecha.isoformat(),
            semana=reg.semana,
            created_at=reg.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar IVR: {exc}") from exc


@router.delete("/api/ivr/{registro_id}")
async def eliminar_ivr(registro_id: int, db: Session = Depends(get_db)):
    try:
        if not IvrService.eliminar(db, registro_id):
            raise HTTPException(status_code=404, detail="Registro IVR no encontrado.")
        return {"ok": True, "mensaje": "Registro IVR eliminado."}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar IVR: {exc}") from exc


@router.get("/api/ivr/exportar")
async def exportar_ivr(
    semana: str = Query("", description="Semana ISO ej: 2026-W25"),
    db: Session = Depends(get_db),
):
    try:
        sem = semana.strip() or None
        content = IvrService.exportar_excel(db, sem)
        semana_archivo = sem or IvrService.semana_iso()
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=reporte_ivr_{semana_archivo}.xlsx"
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al exportar IVR: {exc}") from exc