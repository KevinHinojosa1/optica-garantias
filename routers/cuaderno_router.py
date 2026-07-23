"""Router del Cuaderno de anotaciones creativo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from schemas.cuaderno import CuadernoListResponse, CuadernoNotaCreate, CuadernoNotaUpdate
from services.actividad_service import ActividadService
from services.cuaderno_service import CuadernoService
from templates_shared import templates

router = APIRouter(tags=["Cuaderno"])


@router.get("/cuaderno", response_class=HTMLResponse)
async def pagina_cuaderno(request: Request):
    return templates.TemplateResponse(
        request,
        "cuaderno.html",
        {"active": "cuaderno"},
    )


@router.get("/api/cuaderno", response_model=CuadernoListResponse)
async def api_listar(
    q: str = Query(""),
    categoria: str = Query(""),
    fijadas: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    data = CuadernoService.listar(
        db, q=q, categoria=categoria, solo_fijadas=fijadas, limit=limit
    )
    return CuadernoListResponse(**data)


@router.post("/api/cuaderno")
async def api_crear(payload: CuadernoNotaCreate, db: Session = Depends(get_db)):
    try:
        return CuadernoService.crear(
            db,
            titulo=payload.titulo,
            contenido=payload.contenido,
            emoji=payload.emoji,
            color=payload.color,
            categoria=payload.categoria,
            tags=payload.tags,
            fijada=payload.fijada,
            autor=payload.autor or settings.default_asesor,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/actividad")
async def api_actividad(
    limit: int = Query(40, ge=1, le=200),
    modulo: str = Query(""),
    db: Session = Depends(get_db),
):
    return {"items": ActividadService.listar(limit=limit, modulo=modulo, db=db)}


@router.get("/api/cuaderno/adjuntos/{adj_id}")
async def api_adjunto(adj_id: int, db: Session = Depends(get_db)):
    adj = CuadernoService.obtener_adjunto(db, adj_id)
    if not adj:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    path = settings.base_dir / adj.ruta
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    return FileResponse(path, media_type=adj.mime or "image/jpeg", filename=adj.nombre_original)


@router.delete("/api/cuaderno/adjuntos/{adj_id}")
async def api_eliminar_adjunto(adj_id: int, db: Session = Depends(get_db)):
    if not CuadernoService.eliminar_adjunto(db, adj_id):
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return {"ok": True}


@router.get("/api/cuaderno/{nota_id}")
async def api_obtener(nota_id: int, db: Session = Depends(get_db)):
    nota = CuadernoService.obtener(db, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return CuadernoService._to_dict(nota)


@router.put("/api/cuaderno/{nota_id}")
async def api_actualizar(nota_id: int, payload: CuadernoNotaUpdate, db: Session = Depends(get_db)):
    datos = payload.model_dump(exclude_unset=True)
    out = CuadernoService.actualizar(db, nota_id, datos)
    if not out:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return out


@router.delete("/api/cuaderno/{nota_id}")
async def api_eliminar(nota_id: int, db: Session = Depends(get_db)):
    if not CuadernoService.eliminar(db, nota_id):
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return {"ok": True}


@router.post("/api/cuaderno/{nota_id}/imagen")
async def api_subir_imagen(
    nota_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not archivo.content_type or not archivo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes.")
    content = await archivo.read()
    try:
        out = CuadernoService.agregar_imagen(
            db,
            nota_id,
            content=content,
            filename=archivo.filename or "imagen.jpg",
            mime=archivo.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not out:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return out
