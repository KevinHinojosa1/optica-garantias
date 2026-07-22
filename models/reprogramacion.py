"""Modelo de reprogramaciones de entrega / envíos WhatsApp guardados en BD."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ReprogramacionEnvio(Base):
    """Registro de un aviso de reprogramación (cliente, tienda o correo)."""

    __tablename__ = "reprogramacion_envios"
    __table_args__ = (
        Index("ix_reprog_fecha_local", "fecha", "local"),
        Index("ix_reprog_factura", "factura"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    local: Mapped[str] = mapped_column(String(200), nullable=False, index=True, default="Sin tienda")
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    producto: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    factura: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    telefono: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    canal: Mapped[str] = mapped_column(String(30), nullable=False, default="cliente", index=True)
    estado: Mapped[str] = mapped_column(String(80), nullable=False, default="Mensaje generado")
    asesor: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_tienda: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    motivo: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    fecha_reprogramada: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    fecha_anterior: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    lote_id: Mapped[str] = mapped_column(String(60), nullable=False, default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
