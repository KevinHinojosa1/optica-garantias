from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from templates_shared import templates
from sqlalchemy.orm import Session

from database import get_db
from schemas.cliente import ImportResult
from services.import_service import ImportService
from services.tiendas_service import TiendasService

router = APIRouter(tags=["Módulo 1 - Importación"])



@router.get("/importar", response_class=HTMLResponse)
async def pagina_importar(request: Request):
    ruta_base = ImportService.ruta_archivo_base()
    return templates.TemplateResponse(
        request,
        "importar.html",
        {
            "active": "importar",
            "tiendas": TiendasService.listar(),
            "ruta_base_datos": str(ruta_base),
            "existe_archivo_base": ruta_base.exists(),
        },
    )


@router.post("/api/importar", response_model=ImportResult)
async def importar_archivo(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not archivo.filename:
        raise HTTPException(status_code=400, detail="No se recibió ningún archivo.")

    allowed = (".csv", ".xlsx", ".xls")
    if not archivo.filename.lower().endswith(allowed):
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Suba un archivo CSV o Excel (.xlsx).",
        )

    try:
        content = await archivo.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        result = ImportService.import_to_db(db, content, archivo.filename)
        return ImportResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar: {exc}") from exc


@router.post("/api/importar/carpeta", response_model=ImportResult)
async def importar_desde_carpeta(
    reemplazar: bool = Query(True, description="Si true, borra la base actual e importa el Excel de la carpeta"),
    db: Session = Depends(get_db),
):
    try:
        result = ImportService.importar_desde_carpeta(db, reemplazar=reemplazar)
        return ImportResult(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al importar desde carpeta: {exc}") from exc


@router.delete("/api/importar/limpiar")
async def limpiar_base_datos(db: Session = Depends(get_db)):
    try:
        eliminados = ImportService.limpiar_todos(db)
        return {"ok": True, "eliminados": eliminados, "mensaje": f"Se eliminaron {eliminados} paciente(s)."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al limpiar: {exc}") from exc