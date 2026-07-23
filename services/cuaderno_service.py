"""Cuaderno de anotaciones — notas creativas con imágenes."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, joinedload

from config import settings
from models.cuaderno import CuadernoAdjunto, CuadernoNota
from services.actividad_service import ActividadService

CATEGORIAS = [
    {"id": "general", "label": "General", "emoji": "📝"},
    {"id": "clientes", "label": "Clientes", "emoji": "👤"},
    {"id": "tiendas", "label": "Tiendas", "emoji": "🏬"},
    {"id": "garantias", "label": "Garantías", "emoji": "🛡️"},
    {"id": "entregas", "label": "Entregas", "emoji": "📦"},
    {"id": "alertas", "label": "Alertas", "emoji": "📡"},
    {"id": "ideas", "label": "Ideas", "emoji": "💡"},
    {"id": "urgente", "label": "Urgente", "emoji": "🔥"},
]

COLORES = ["amber", "rose", "sky", "emerald", "violet", "orange", "slate"]


class CuadernoService:
    @classmethod
    def dir_adjuntos(cls) -> Path:
        p = settings.base_dir / "data" / "cuaderno"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def _to_dict(cls, nota: CuadernoNota) -> dict[str, Any]:
        return {
            "id": nota.id,
            "titulo": nota.titulo,
            "contenido": nota.contenido,
            "emoji": nota.emoji or "📝",
            "color": nota.color or "amber",
            "categoria": nota.categoria or "general",
            "tags": [t for t in (nota.tags or "").split(",") if t.strip()],
            "tags_raw": nota.tags or "",
            "fijada": bool(nota.fijada),
            "autor": nota.autor or "",
            "created_at": nota.created_at.isoformat() if nota.created_at else "",
            "updated_at": nota.updated_at.isoformat() if nota.updated_at else "",
            "adjuntos": [
                {
                    "id": a.id,
                    "nombre": a.nombre_original,
                    "url": f"/api/cuaderno/adjuntos/{a.id}",
                    "mime": a.mime,
                }
                for a in (nota.adjuntos or [])
            ],
        }

    @classmethod
    def listar(
        cls,
        db: Session,
        *,
        q: str = "",
        categoria: str = "",
        solo_fijadas: bool = False,
        limit: int = 200,
    ) -> dict[str, Any]:
        query = db.query(CuadernoNota).options(joinedload(CuadernoNota.adjuntos))
        if categoria:
            query = query.filter(CuadernoNota.categoria == categoria)
        if solo_fijadas:
            query = query.filter(CuadernoNota.fijada.is_(True))
        if q.strip():
            like = f"%{q.strip()}%"
            query = query.filter(
                (CuadernoNota.titulo.ilike(like))
                | (CuadernoNota.contenido.ilike(like))
                | (CuadernoNota.tags.ilike(like))
            )
        rows = (
            query.order_by(CuadernoNota.fijada.desc(), CuadernoNota.updated_at.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        notas = [cls._to_dict(n) for n in rows]
        # Agrupar por mes para vista "cuaderno físico"
        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        }
        por_mes: dict[str, list] = {}
        for n in notas:
            raw = n.get("updated_at") or n.get("created_at") or ""
            try:
                dt = datetime.fromisoformat(raw.replace("Z", ""))
                clave = f"{meses_es.get(dt.month, dt.month)} {dt.year}"
            except Exception:
                clave = "Sin fecha"
            por_mes.setdefault(clave, []).append(n)
        secciones = [{"mes": k, "notas": v, "total": len(v)} for k, v in por_mes.items()]
        return {
            "total": len(rows),
            "notas": notas,
            "secciones": secciones,
            "categorias": CATEGORIAS,
            "colores": COLORES,
        }

    @classmethod
    def obtener(cls, db: Session, nota_id: int) -> CuadernoNota | None:
        return (
            db.query(CuadernoNota)
            .options(joinedload(CuadernoNota.adjuntos))
            .filter(CuadernoNota.id == nota_id)
            .first()
        )

    @classmethod
    def crear(
        cls,
        db: Session,
        *,
        titulo: str,
        contenido: str = "",
        emoji: str = "📝",
        color: str = "amber",
        categoria: str = "general",
        tags: str = "",
        fijada: bool = False,
        autor: str = "",
    ) -> dict[str, Any]:
        nota = CuadernoNota(
            titulo=(titulo or "Sin título").strip()[:250],
            contenido=contenido or "",
            emoji=(emoji or "📝")[:16],
            color=color if color in COLORES else "amber",
            categoria=categoria or "general",
            tags=cls._norm_tags(tags),
            fijada=fijada,
            autor=autor or settings.default_asesor,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(nota)
        db.commit()
        db.refresh(nota)
        ActividadService.registrar(
            modulo="cuaderno",
            accion="crear_nota",
            detalle=nota.titulo,
            usuario=nota.autor,
            entidad="nota",
            entidad_id=str(nota.id),
            db=db,
        )
        return cls._to_dict(nota)

    @classmethod
    def actualizar(cls, db: Session, nota_id: int, datos: dict[str, Any]) -> dict[str, Any] | None:
        nota = cls.obtener(db, nota_id)
        if not nota:
            return None
        if "titulo" in datos:
            nota.titulo = (datos["titulo"] or "Sin título").strip()[:250]
        if "contenido" in datos:
            nota.contenido = datos["contenido"] or ""
        if "emoji" in datos:
            nota.emoji = (datos["emoji"] or "📝")[:16]
        if "color" in datos and datos["color"] in COLORES:
            nota.color = datos["color"]
        if "categoria" in datos:
            nota.categoria = datos["categoria"] or "general"
        if "tags" in datos:
            nota.tags = cls._norm_tags(datos["tags"])
        if "fijada" in datos:
            nota.fijada = bool(datos["fijada"])
        if "autor" in datos and datos["autor"]:
            nota.autor = datos["autor"]
        nota.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(nota)
        ActividadService.registrar(
            modulo="cuaderno",
            accion="editar_nota",
            detalle=nota.titulo,
            usuario=nota.autor,
            entidad="nota",
            entidad_id=str(nota.id),
            db=db,
        )
        return cls._to_dict(nota)

    @classmethod
    def eliminar(cls, db: Session, nota_id: int) -> bool:
        nota = cls.obtener(db, nota_id)
        if not nota:
            return False
        for a in list(nota.adjuntos or []):
            path = settings.base_dir / a.ruta
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
        titulo = nota.titulo
        db.delete(nota)
        db.commit()
        ActividadService.registrar(
            modulo="cuaderno",
            accion="eliminar_nota",
            detalle=titulo,
            entidad="nota",
            entidad_id=str(nota_id),
            db=db,
        )
        return True

    @classmethod
    def agregar_imagen(
        cls,
        db: Session,
        nota_id: int,
        *,
        content: bytes,
        filename: str,
        mime: str,
    ) -> dict[str, Any] | None:
        nota = cls.obtener(db, nota_id)
        if not nota:
            return None
        if not content:
            raise ValueError("Imagen vacía")
        ext = Path(filename or "img.jpg").suffix.lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            ext = ".jpg"
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(filename or "imagen").stem)[:40]
        nombre = f"nota_{nota_id}_{uuid.uuid4().hex[:8]}_{safe}{ext}"
        rel = Path("data/cuaderno") / nombre
        abs_path = settings.base_dir / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(content)
        adj = CuadernoAdjunto(
            nota_id=nota_id,
            nombre_original=filename or nombre,
            ruta=str(rel).replace("\\", "/"),
            mime=mime or "image/jpeg",
            created_at=datetime.utcnow(),
        )
        db.add(adj)
        nota.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(nota)
        return cls._to_dict(nota)

    @classmethod
    def obtener_adjunto(cls, db: Session, adj_id: int) -> CuadernoAdjunto | None:
        return db.query(CuadernoAdjunto).filter(CuadernoAdjunto.id == adj_id).first()

    @classmethod
    def eliminar_adjunto(cls, db: Session, adj_id: int) -> bool:
        adj = cls.obtener_adjunto(db, adj_id)
        if not adj:
            return False
        path = settings.base_dir / adj.ruta
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        nota_id = adj.nota_id
        db.delete(adj)
        nota = cls.obtener(db, nota_id)
        if nota:
            nota.updated_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def _norm_tags(tags) -> str:
        if isinstance(tags, list):
            parts = [str(t).strip() for t in tags if str(t).strip()]
        else:
            parts = [t.strip() for t in str(tags or "").replace(";", ",").split(",") if t.strip()]
        return ",".join(parts[:20])
