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
    try:
        total_consultas = db.query(func.count(HistorialConsulta.id)).scalar() or 0
        aprobadas = db.query(func.count(HistorialConsulta.id)).filter(HistorialConsulta.veredicto.in_(["APLICA", "SI APLICA", "SÍ APLICA"])).scalar() or 0
        rechazadas = db.query(func.count(HistorialConsulta.id)).filter(HistorialConsulta.veredicto.in_(["NO APLICA"])).scalar() or 0
        dudosas = max(0, total_consultas - aprobadas - rechazadas)
        ultimas = db.query(HistorialConsulta).order_by(HistorialConsulta.created_at.desc()).limit(6).all()
        porcentaje_aprobacion = round((aprobadas / total_consultas * 100), 1) if total_consultas > 0 else 0

        # Top motivos
        motivos_rows = (
            db.query(HistorialConsulta.motivo, func.count(HistorialConsulta.id).label("cnt"))
            .filter(HistorialConsulta.motivo.isnot(None), HistorialConsulta.motivo != "")
            .group_by(HistorialConsulta.motivo)
            .order_by(func.count(HistorialConsulta.id).desc())
            .limit(5)
            .all()
        )
        motivos_stats = [
            {
                "motivo": (m[0] or "Evaluación general")[:65],
                "count": m[1],
                "pct": round((m[1] / total_consultas * 100), 1) if total_consultas > 0 else 0,
            }
            for m in motivos_rows
        ]

        # Top asesores / actividad
        asesores_rows = (
            db.query(HistorialConsulta.asesor, func.count(HistorialConsulta.id).label("cnt"))
            .filter(HistorialConsulta.asesor.isnot(None), HistorialConsulta.asesor != "")
            .group_by(HistorialConsulta.asesor)
            .order_by(func.count(HistorialConsulta.id).desc())
            .limit(5)
            .all()
        )
        locales_stats = [
            {"tienda": a[0] or "SAC Central", "count": a[1]}
            for a in asesores_rows
        ]
    except Exception as exc:
        print(f"Error cargando métricas de dashboard: {exc}", flush=True)
        total_consultas = 0
        aprobadas = 0
        rechazadas = 0
        dudosas = 0
        ultimas = []
        porcentaje_aprobacion = 0
        motivos_stats = []
        locales_stats = []

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "total_consultas": total_consultas,
            "total_casos": total_consultas,
            "aprobadas": aprobadas,
            "rechazadas": rechazadas,
            "dudosas": dudosas,
            "revisar": dudosas,
            "porcentaje_aprobacion": porcentaje_aprobacion,
            "ultimas": ultimas,
            "ultimos_casos": ultimas,
            "motivos_stats": motivos_stats,
            "locales_stats": locales_stats,
        },
    )
