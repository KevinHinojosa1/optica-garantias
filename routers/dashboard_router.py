from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from templates_shared import templates
from database import get_db
from models.historial import HistorialConsulta

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
async def ver_dashboard(request: Request, db: Session = Depends(get_db)):
    total_consultas = db.query(func.count(HistorialConsulta.id)).scalar()
    aprobadas = db.query(func.count(HistorialConsulta.id)).filter(HistorialConsulta.veredicto == 'APLICA').scalar()
    rechazadas = db.query(func.count(HistorialConsulta.id)).filter(HistorialConsulta.veredicto == 'NO APLICA').scalar()
    dudosas = db.query(func.count(HistorialConsulta.id)).filter(HistorialConsulta.veredicto == 'IMAGEN NO CLARA').scalar()
    
    # Obtener ultimas consultas
    ultimas = db.query(HistorialConsulta).order_by(HistorialConsulta.created_at.desc()).limit(5).all()

    porcentaje_aprobacion = round((aprobadas / total_consultas * 100), 1) if total_consultas > 0 else 0

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "total_consultas": total_consultas,
            "aprobadas": aprobadas,
            "rechazadas": rechazadas,
            "dudosas": dudosas,
            "porcentaje_aprobacion": porcentaje_aprobacion,
            "ultimas": ultimas,
        },
    )
