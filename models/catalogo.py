"""Catálogos y plantillas persistidos en BD (scripts, plantillas bot, etc.)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CatalogoJson(Base):
    """Documento JSON versionado (scripts CX, configs grandes)."""

    __tablename__ = "catalogos_json"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clave: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PlantillaBot(Base):
    """Plantillas guardadas del bot / respuesta IA."""

    __tablename__ = "plantillas_bot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    modulo: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    mensaje_whatsapp: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mensaje_correo: Mapped[str] = mapped_column(Text, default="", nullable=False)
    asunto_correo: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
