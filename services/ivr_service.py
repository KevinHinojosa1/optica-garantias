import io
from datetime import date, datetime

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.ivr import IvrVerificacion
from services.google_sheets_service import GoogleSheetsService
from services.tiendas_service import TiendasService


class IvrService:
    @staticmethod
    def semana_iso(fecha: date | None = None) -> str:
        f = fecha or date.today()
        year, week, _ = f.isocalendar()
        return f"{year}-W{week:02d}"

    @classmethod
    def registrar(
        cls,
        db: Session,
        *,
        tienda_id: str,
        funciona: bool,
        comentario: str = "",
        verificado_por: str = "Sistema",
    ) -> dict:
        tienda = TiendasService.obtener(tienda_id)
        if not tienda or tienda["id"] == "central-call-center":
            raise ValueError("Tienda no válida para verificación IVR.")

        ahora = datetime.utcnow()
        hoy = ahora.date()
        semana = cls.semana_iso(hoy)

        registro = IvrVerificacion(
            tienda_id=tienda_id,
            tienda_nombre=tienda["nombre"],
            ciudad=tienda["ciudad"],
            funciona=funciona,
            comentario=comentario.strip() or None,
            verificado_por=verificado_por.strip() or "Sistema",
            fecha=hoy,
            semana=semana,
            created_at=ahora,
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)

        sheets = GoogleSheetsService.registrar_ivr(
            fecha=hoy,
            hora=ahora,
            semana=semana,
            tienda_nombre=tienda["nombre"],
            ciudad=tienda["ciudad"],
            funciona=funciona,
            comentario=comentario,
            verificado_por=verificado_por,
        )

        return {
            "registro": registro,
            "google_sheets": sheets,
        }

    @staticmethod
    def ultimo_por_tienda(db: Session) -> dict[str, IvrVerificacion]:
        sub = (
            db.query(IvrVerificacion.tienda_id, func.max(IvrVerificacion.id).label("max_id"))
            .group_by(IvrVerificacion.tienda_id)
            .subquery()
        )
        registros = (
            db.query(IvrVerificacion)
            .join(sub, IvrVerificacion.id == sub.c.max_id)
            .all()
        )
        return {r.tienda_id: r for r in registros}

    @staticmethod
    def obtener(db: Session, registro_id: int) -> IvrVerificacion | None:
        return db.query(IvrVerificacion).filter(IvrVerificacion.id == registro_id).first()

    @classmethod
    def actualizar(
        cls,
        db: Session,
        registro_id: int,
        *,
        funciona: bool,
        comentario: str = "",
        verificado_por: str = "Sistema",
    ) -> IvrVerificacion:
        registro = cls.obtener(db, registro_id)
        if not registro:
            raise ValueError("Registro IVR no encontrado.")
        registro.funciona = funciona
        registro.comentario = comentario.strip() or None
        registro.verificado_por = verificado_por.strip() or "Sistema"
        db.commit()
        db.refresh(registro)
        return registro

    @classmethod
    def eliminar(cls, db: Session, registro_id: int) -> bool:
        registro = cls.obtener(db, registro_id)
        if not registro:
            return False
        db.delete(registro)
        db.commit()
        return True

    @staticmethod
    def listar_recientes(db: Session, limit: int = 100) -> list[IvrVerificacion]:
        return (
            db.query(IvrVerificacion)
            .order_by(IvrVerificacion.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def resumen_semana(db: Session, semana: str | None = None) -> list[dict]:
        sem = semana or IvrService.semana_iso()
        tiendas = [t for t in TiendasService.listar() if t["id"] != "central-call-center"]
        ultimos = IvrService.ultimo_por_tienda(db)

        filas = []
        for t in tiendas:
            u = ultimos.get(t["id"])
            if u and u.semana == sem:
                filas.append(
                    {
                        "tienda_id": t["id"],
                        "tienda_nombre": t["nombre"],
                        "ciudad": t["ciudad"],
                        "funciona": u.funciona,
                        "comentario": u.comentario,
                        "verificado_at": u.created_at.isoformat(),
                        "verificado_por": u.verificado_por,
                        "semana": u.semana,
                    }
                )
            else:
                filas.append(
                    {
                        "tienda_id": t["id"],
                        "tienda_nombre": t["nombre"],
                        "ciudad": t["ciudad"],
                        "funciona": None,
                        "comentario": None,
                        "verificado_at": None,
                        "verificado_por": None,
                        "semana": sem,
                    }
                )
        return filas

    @staticmethod
    def exportar_excel(db: Session, semana: str | None = None) -> bytes:
        sem = semana or IvrService.semana_iso()
        resumen = IvrService.resumen_semana(db, sem)
        registros = IvrService.listar_recientes(db, limit=10_000)

        filas_resumen = [
            {
                "Ciudad": r["ciudad"],
                "Tienda": r["tienda_nombre"],
                "Estado": (
                    "Funciona" if r["funciona"] is True
                    else "No funciona" if r["funciona"] is False
                    else "Sin verificar"
                ),
                "Comentario": r["comentario"] or "",
                "Verificador": r["verificado_por"] or "",
                "Última verificación": (
                    datetime.fromisoformat(r["verificado_at"]).strftime("%Y-%m-%d %H:%M")
                    if r["verificado_at"]
                    else ""
                ),
                "Semana": r["semana"],
            }
            for r in resumen
        ]
        filas_historial = [
            {
                "Fecha/Hora": r.created_at.strftime("%Y-%m-%d %H:%M"),
                "Semana": r.semana,
                "Ciudad": r.ciudad,
                "Tienda": r.tienda_nombre,
                "Estado": "Funciona" if r.funciona else "No funciona",
                "Comentario": r.comentario or "",
                "Verificador": r.verificado_por,
            }
            for r in registros
        ]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(filas_resumen).to_excel(
                writer, index=False, sheet_name=f"Resumen {sem}"
            )
            pd.DataFrame(filas_historial).to_excel(
                writer, index=False, sheet_name="Historial"
            )
        buffer.seek(0)
        return buffer.getvalue()