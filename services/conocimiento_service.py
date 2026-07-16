"""Base de conocimiento oficial — alimenta el veredicto Claude (RAG)."""

from __future__ import annotations

import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from config import settings
from models.conocimiento import ConocimientoItem

CONOCIMIENTO_DIR = settings.base_dir / "data" / "conocimiento"

CATEGORIAS = [
    {"id": "politica_oficial", "label": "Política oficial", "icon": "📜"},
    {"id": "caso_aplica", "label": "Caso que APLICA", "icon": "✅"},
    {"id": "caso_no_aplica", "label": "Caso que NO APLICA", "icon": "❌"},
    {"id": "guia_visual", "label": "Guía visual (con imagen)", "icon": "🖼️"},
    {"id": "procedimiento", "label": "Procedimiento / flujo", "icon": "📋"},
]

SEED_ENTRIES: list[dict[str, Any]] = [
    {
        "titulo": "Garantía APLICA — defectos de fabricación",
        "categoria": "politica_oficial",
        "tags": "aplica,garantia,fisura,armazon,bisagra,AR,defecto,fabricacion",
        "prioridad": 90,
        "contenido": (
            "APLICA garantía del proveedor (1 año desde factura): fisura en montura sin golpe, "
            "desprendimiento capa AR sin rayas ni químicos, defecto en bisagras/soldaduras, "
            "fisura en perforación o bordes del lente (excepto CR39 hasta 6 meses), "
            "defecto borde lente de contacto (reclamo 24h con caja), tonalidad distinta entre LC."
        ),
    },
    {
        "titulo": "Garantía NO APLICA — daño por uso o maltrato",
        "categoria": "politica_oficial",
        "tags": "no aplica,craquelado,picado,raya,quimico,golpe,terceros,descuento",
        "prioridad": 90,
        "contenido": (
            "NO APLICA: lente craquelado (microfisuras por golpe/calor), lente picado o rayado por uso, "
            "limpieza inadecuada, sprays/químicos, reparación por terceros, descuento >=30%, "
            "promoción 2x1 precio $0."
        ),
    },
    {
        "titulo": "Plazos especiales de garantía",
        "categoria": "politica_oficial",
        "tags": "plazo,dias,habiles,gafas,cambio,adaptacion,AR,contacto",
        "prioridad": 85,
        "contenido": (
            "Plazos: cambio modelo gafas 3 días hábiles; adaptación medida oftálmicos 1 mes; "
            "desprendimiento AR 12 meses desde entrega; fisuras bordes (no CR39) 6 meses; "
            "armazones defecto fábrica 1 año; LC defecto máximo 24 horas."
        ),
    },
    {
        "titulo": "Ejemplo visual — lente craquelado (NO APLICA)",
        "categoria": "caso_no_aplica",
        "tags": "craquelado,red,microfisuras,golpe,no aplica,imagen",
        "prioridad": 80,
        "contenido": (
            "Red de microfisuras en superficie del lente indica impacto, calor o mal almacenamiento. "
            "Veredicto habitual: NO APLICA. Fundamento: daño por uso, no defecto de fábrica."
        ),
    },
    {
        "titulo": "Ejemplo — desprendimiento AR sin rayas (APLICA)",
        "categoria": "caso_aplica",
        "tags": "AR,anti-reflejo,desprendimiento,aplica,defecto",
        "prioridad": 80,
        "contenido": (
            "Si la capa anti-reflejo se desprende sin rayaduras ni evidencia de químicos, "
            "clasificar como defecto de fabricación. Veredicto: APLICA dentro de 12 meses desde entrega."
        ),
    },
]


def _normalizar(texto: str) -> str:
    t = (texto or "").lower()
    t = re.sub(r"[áàä]", "a", t)
    t = re.sub(r"[éèë]", "e", t)
    t = re.sub(r"[íìï]", "i", t)
    t = re.sub(r"[óòö]", "o", t)
    t = re.sub(r"[úùü]", "u", t)
    t = re.sub(r"ñ", "n", t)
    return t


def _tokens(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", _normalizar(texto))}


class ConocimientoService:
    @staticmethod
    def _to_response(item: ConocimientoItem) -> dict[str, Any]:
        data = {
            "id": item.id,
            "titulo": item.titulo,
            "categoria": item.categoria,
            "contenido": item.contenido,
            "tags": item.tags,
            "imagen_path": item.imagen_path,
            "imagen_url": f"/api/conocimiento/imagen/{item.id}" if item.imagen_path else None,
            "fuente": item.fuente,
            "prioridad": item.prioridad,
            "activo": item.activo,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        return data

    @classmethod
    def listar(cls, db: Session, *, solo_activos: bool = False) -> dict[str, Any]:
        q = db.query(ConocimientoItem).order_by(
            ConocimientoItem.prioridad.desc(),
            ConocimientoItem.updated_at.desc(),
        )
        if solo_activos:
            q = q.filter(ConocimientoItem.activo.is_(True))
        items = q.all()
        activos = sum(1 for i in items if i.activo)
        return {
            "total": len(items),
            "activos": activos,
            "items": [cls._to_response(i) for i in items],
            "categorias": CATEGORIAS,
        }

    @classmethod
    def obtener(cls, db: Session, item_id: int) -> ConocimientoItem | None:
        return db.query(ConocimientoItem).filter(ConocimientoItem.id == item_id).first()

    @classmethod
    def crear(
        cls,
        db: Session,
        data: dict[str, Any],
        imagen_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        item = ConocimientoItem(
            titulo=data["titulo"].strip(),
            categoria=data.get("categoria", "politica_oficial"),
            contenido=data["contenido"].strip(),
            tags=(data.get("tags") or "").strip(),
            fuente=(data.get("fuente") or "Óptica Los Andes").strip(),
            prioridad=int(data.get("prioridad", 50)),
            activo=bool(data.get("activo", True)),
        )
        db.add(item)
        db.flush()
        if imagen_bytes:
            item.imagen_path = cls._guardar_imagen(item.id, imagen_bytes, mime_type)
        db.commit()
        db.refresh(item)
        return cls._to_response(item)

    @classmethod
    def actualizar(
        cls,
        db: Session,
        item_id: int,
        data: dict[str, Any],
        imagen_bytes: bytes | None = None,
        mime_type: str | None = None,
        quitar_imagen: bool = False,
    ) -> dict[str, Any]:
        item = cls.obtener(db, item_id)
        if not item:
            raise ValueError("Entrada no encontrada.")
        for campo in ("titulo", "categoria", "contenido", "tags", "fuente", "prioridad", "activo"):
            if campo in data and data[campo] is not None:
                setattr(item, campo, data[campo])
        item.updated_at = datetime.utcnow()
        if quitar_imagen and item.imagen_path:
            cls._eliminar_archivo(item.imagen_path)
            item.imagen_path = None
        if imagen_bytes:
            if item.imagen_path:
                cls._eliminar_archivo(item.imagen_path)
            item.imagen_path = cls._guardar_imagen(item.id, imagen_bytes, mime_type)
        db.commit()
        db.refresh(item)
        return cls._to_response(item)

    @classmethod
    def eliminar(cls, db: Session, item_id: int) -> None:
        item = cls.obtener(db, item_id)
        if not item:
            raise ValueError("Entrada no encontrada.")
        if item.imagen_path:
            cls._eliminar_archivo(item.imagen_path)
        db.delete(item)
        db.commit()

    @classmethod
    def _guardar_imagen(cls, item_id: int, content: bytes, mime_type: str | None) -> str:
        CONOCIMIENTO_DIR.mkdir(parents=True, exist_ok=True)
        ext = mimetypes.guess_extension(mime_type or "image/jpeg") or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        nombre = f"kb_{item_id}{ext}"
        ruta = CONOCIMIENTO_DIR / nombre
        ruta.write_bytes(content)
        return str(Path("data/conocimiento") / nombre)

    @classmethod
    def _eliminar_archivo(cls, rel_path: str) -> None:
        ruta = settings.base_dir / rel_path
        if ruta.exists():
            ruta.unlink(missing_ok=True)

    @classmethod
    def ruta_imagen_abs(cls, item: ConocimientoItem) -> Path | None:
        if not item.imagen_path:
            return None
        ruta = settings.base_dir / item.imagen_path
        return ruta if ruta.exists() else None

    @classmethod
    def buscar_relevantes(
        cls,
        db: Session,
        contexto_cliente: dict,
        *,
        limit: int = 8,
    ) -> list[ConocimientoItem]:
        items = (
            db.query(ConocimientoItem)
            .filter(ConocimientoItem.activo.is_(True))
            .all()
        )
        if not items:
            return []

        consulta = " ".join(
            str(contexto_cliente.get(k, "") or "")
            for k in (
                "producto", "tipo_producto", "estado_garantia",
                "dentro_garantia", "tiene_ola_plus", "dias_desde_factura",
            )
        )
        q_tokens = _tokens(consulta)

        scored: list[tuple[int, ConocimientoItem]] = []
        for item in items:
            score = item.prioridad
            blob = f"{item.titulo} {item.tags} {item.contenido} {item.categoria}"
            i_tokens = _tokens(blob)
            overlap = len(q_tokens & i_tokens)
            score += overlap * 12
            if item.imagen_path:
                score += 5
            if item.categoria == "guia_visual":
                score += 8
            if item.categoria == "caso_aplica" and contexto_cliente.get("dentro_garantia"):
                score += 6
            if item.categoria == "caso_no_aplica":
                score += 4
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    @classmethod
    def construir_bloque_prompt(cls, items: list[ConocimientoItem]) -> str:
        if not items:
            return ""
        lineas = [
            "BASE DE CONOCIMIENTO OFICIAL (nutrida por Óptica Los Andes — priorizar sobre reglas genéricas):",
        ]
        for i, item in enumerate(items, 1):
            cat = next((c["label"] for c in CATEGORIAS if c["id"] == item.categoria), item.categoria)
            lineas.append(f"\n[{i}] {cat} — {item.titulo}")
            if item.tags:
                lineas.append(f"Tags: {item.tags}")
            lineas.append(item.contenido.strip())
            if item.imagen_path:
                lineas.append("(Incluye imagen de referencia oficial adjunta en este análisis.)")
        lineas.append(
            "\nUsa esta base para el fundamento del veredicto. Cita el título del documento cuando aplique."
        )
        return "\n".join(lineas)

    @classmethod
    def items_con_imagen(cls, items: list[ConocimientoItem], max_imagenes: int = 2) -> list[ConocimientoItem]:
        out = []
        for item in items:
            if item.imagen_path and cls.ruta_imagen_abs(item):
                out.append(item)
            if len(out) >= max_imagenes:
                break
        return out

    @classmethod
    def fuentes_resumen(cls, items: list[ConocimientoItem]) -> list[dict[str, Any]]:
        return [
            {
                "id": i.id,
                "titulo": i.titulo,
                "categoria": i.categoria,
                "tiene_imagen": bool(i.imagen_path),
            }
            for i in items
        ]

    @classmethod
    def sembrar_inicial(cls, db: Session) -> int:
        if db.query(ConocimientoItem).count() > 0:
            return 0
        for entry in SEED_ENTRIES:
            db.add(ConocimientoItem(**entry, fuente="Políticas Óptica Los Andes", activo=True))
        db.commit()
        return len(SEED_ENTRIES)