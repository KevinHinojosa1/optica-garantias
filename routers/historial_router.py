from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.cliente import Cliente
from schemas.historial import HistorialResponse
from services.historial_service import HistorialService
from services.pdf_service import PdfService

router = APIRouter(tags=["Módulo 5 - Historial"])
templates = Jinja2Templates(directory="templates")

POLITICAS = [
    {
        "titulo": "Nota de crédito",
        "texto": "Las devoluciones se realizan SOLO mediante Nota de Crédito con vigencia de 1 año. No hay reembolsos en efectivo.",
    },
    {
        "titulo": "Inicio de garantía",
        "texto": "La garantía aplica desde la fecha de FACTURACIÓN, no desde la fecha de entrega.",
    },
    {
        "titulo": "Sin garantía",
        "texto": "Líquidos y accesorios NO tienen garantía.",
    },
    {
        "titulo": "Productos abandonados",
        "texto": "Productos abandonados más de 90 días en local: la empresa no asume responsabilidad.",
    },
    {
        "titulo": "Compras online",
        "texto": "Devolución solo si el producto llega diferente a lo comprado online (reportar máximo 3 días hábiles después de recibir).",
    },
    {
        "titulo": "OLA Plus",
        "texto": "Garantía extendida hasta 360 días incluyendo robo y daño accidental (alianza AIG-Metropolitana).",
    },
    {
        "titulo": "Gafas — cambio de modelo",
        "texto": "Solo 3 días hábiles desde la compra, previa verificación del Personal Calificado.",
    },
    {
        "titulo": "Lentes de contacto",
        "texto": "Defecto de fábrica: reclamo inmediato, máximo 24 horas, con caja y blíster.",
    },
]


@router.get("/historial", response_class=HTMLResponse)
async def pagina_historial(request: Request):
    return templates.TemplateResponse(
        request,
        "historial.html",
        {"active": "historial", "politicas": POLITICAS},
    )


@router.get("/api/historial", response_model=list[HistorialResponse])
async def listar_historial(db: Session = Depends(get_db), limit: int = 100):
    try:
        return HistorialService.listar(db, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al cargar historial: {exc}") from exc


@router.get("/api/historial/exportar")
async def exportar_historial(db: Session = Depends(get_db)):
    try:
        content = HistorialService.exportar_excel(db)
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=historial_garantias.xlsx"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al exportar: {exc}") from exc


@router.get("/api/historial/ultimo/{cliente_id}", response_model=HistorialResponse)
async def ultimo_historial_cliente(cliente_id: int, db: Session = Depends(get_db)):
    registro = HistorialService.ultimo_por_cliente(db, cliente_id)
    if not registro:
        raise HTTPException(status_code=404, detail="No hay consultas previas para este cliente.")
    return registro


@router.get("/api/historial/{registro_id}/pdf")
async def descargar_pdf_consulta(registro_id: int, db: Session = Depends(get_db)):
    registro = HistorialService.obtener(db, registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Consulta no encontrada.")
    cliente = None
    if registro.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == registro.cliente_id).first()
    try:
        pdf_bytes = PdfService.generar_informe_consulta(registro, cliente)
        nombre = f"informe_garantia_{registro_id}_{registro.cliente_nombre[:20].replace(' ', '_')}.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {exc}") from exc


@router.delete("/api/historial/{registro_id}")
async def eliminar_consulta(registro_id: int, db: Session = Depends(get_db)):
    try:
        if not HistorialService.eliminar(db, registro_id):
            raise HTTPException(status_code=404, detail="Consulta no encontrada.")
        return {"ok": True, "mensaje": "Consulta eliminada correctamente."}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {exc}") from exc


@router.delete("/api/historial")
async def limpiar_historial(db: Session = Depends(get_db)):
    try:
        eliminados = HistorialService.eliminar_todos(db)
        return {"ok": True, "eliminados": eliminados, "mensaje": f"Se eliminaron {eliminados} consulta(s)."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al limpiar historial: {exc}") from exc