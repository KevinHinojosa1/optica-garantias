"""Cuaderno de anotaciones — notas con imágenes y etiquetas."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CuadernoNota(Base):
    __tablename__ = "cuaderno_notas"
    __table_args__ = (Index("ix_cuaderno_cat_fijada", "categoria", "fijada"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(250), nullable=False, default="Sin título")
    contenido: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="📝")
    color: Mapped[str] = mapped_column(String(40), nullable=False, default="amber")
    categoria: Mapped[str] = mapped_column(String(80), nullable=False, default="general", index=True)
    tags: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    fijada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autor: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )

    adjuntos: Mapped[list["CuadernoAdjunto"]] = relationship(
        "CuadernoAdjunto",
        back_populates="nota",
        cascade="all, delete-orphan",
        order_by="CuadernoAdjunto.id",
    )


class CuadernoAdjunto(Base):
    __tablename__ = "cuaderno_adjuntos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nota_id: Mapped[int] = mapped_column(Integer, ForeignKey("cuaderno_notas.id", ondelete="CASCADE"), index=True)
    nombre_original: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    ruta: Mapped[str] = mapped_column(String(500), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False, default="image/jpeg")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    nota: Mapped["CuadernoNota"] = relationship("CuadernoNota", back_populates="adjuntos")


class ActividadLog(Base):
    """Registro de cambios importantes en el sistema."""

    __tablename__ = "actividad_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False, default="")
    usuario: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    entidad: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    entidad_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
