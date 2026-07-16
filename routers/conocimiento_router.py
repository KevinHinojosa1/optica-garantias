"""Router Base de Conocimiento — nutrir veredictos Claude."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.conocimiento import ConocimientoCreate, ConocimientoListResponse, ConocimientoResponse, ConocimientoUpdate
from services.conocimiento_service import ConocimientoService
from services.respuesta_ia_service import RespuestaIAService
from templates_shared import templates

router = APIRouter(tags=["Base de Conocimiento"])


@router.get("/conocimiento", response_class=HTMLResponse)
async def pagina_conocimiento(request: Request, db: Session = Depends(get_db)):
    ConocimientoService.sembrar_inicial(db)
    meta = ConocimientoService.listar(db)
    ia = RespuestaIAService.ia_disponible()
    return templates.TemplateResponse(
        request,
        "conocimiento.html",
        {
            "active": "conocimiento",
            "meta": meta,
            "ia_disponible": ia["disponible"],
            "ia_modelo": ia["modelo"],
        },
    )


@router.get("/api/conocimiento", response_model=ConocimientoListResponse)
async def api_listar_conocimiento(db: Session = Depends(get_db)):
    ConocimientoService.sembrar_inicial(db)
    return ConocimientoListResponse(**ConocimientoService.listar(db))


@router.post("/api/conocimiento", response_model=ConocimientoResponse)
async def api_crear_conocimiento(
    titulo: str = Form(...),
    categoria: str = Form("politica_oficial"),
    contenido: str = Form(...),
    tags: str = Form(""),
    fuente: str = Form("Óptica Los Andes"),
    prioridad: int = Form(50),
    activo: bool = Form(True),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    try:
        img_bytes = None
        mime = None
        if imagen and imagen.filename:
            if not imagen.content_type or not imagen.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="La imagen debe ser JPG, PNG o WEBP.")
            img_bytes = await imagen.read()
            mime = imagen.content_type
        data = ConocimientoCreate(
            titulo=titulo,
            categoria=categoria,
            contenido=contenido,
            tags=tags,
            fuente=fuente,
            prioridad=prioridad,
            activo=activo,
        ).model_dump()
        return ConocimientoResponse(**ConocimientoService.crear(db, data, img_bytes, mime))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/api/conocimiento/{item_id}", response_model=ConocimientoResponse)
async def api_actualizar_conocimiento(
    item_id: int,
    titulo: str | None = Form(None),
    categoria: str | None = Form(None),
    contenido: str | None = Form(None),
    tags: str | None = Form(None),
    fuente: str | None = Form(None),
    prioridad: int | None = Form(None),
    activo: bool | None = Form(None),
    quitar_imagen: bool = Form(False),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    try:
        payload = ConocimientoUpdate(
            titulo=titulo,
            categoria=categoria,
            contenido=contenido,
            tags=tags,
            fuente=fuente,
            prioridad=prioridad,
            activo=activo,
        ).model_dump(exclude_unset=True)
        img_bytes = None
        mime = None
        if imagen and imagen.filename:
            if not imagen.content_type or not imagen.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="La imagen debe ser JPG, PNG o WEBP.")
            img_bytes = await imagen.read()
            mime = imagen.content_type
        return ConocimientoResponse(
            **ConocimientoService.actualizar(
                db, item_id, payload, img_bytes, mime, quitar_imagen=quitar_imagen
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/api/conocimiento/{item_id}")
async def api_eliminar_conocimiento(item_id: int, db: Session = Depends(get_db)):
    try:
        ConocimientoService.eliminar(db, item_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/conocimiento/imagen/{item_id}")
async def api_imagen_conocimiento(item_id: int, db: Session = Depends(get_db)):
    item = ConocimientoService.obtener(db, item_id)
    if not item or not item.imagen_path:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    ruta = ConocimientoService.ruta_imagen_abs(item)
    if not ruta:
        raise HTTPException(status_code=404, detail="Archivo de imagen no existe.")
    return FileResponse(ruta)