"""Alertas Telegram — filas operativas en base de datos."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AlertaTelegram(Base):
    """Una fila de la matriz GENERAL de alertas (payload JSON completo)."""

    __tablename__ = "alertas_telegram"
    __table_args__ = (
        Index("ix_alerta_estado", "estado_gestion"),
        Index("ix_alerta_local", "local"),
        Index("ix_alerta_fecha", "fecha_alerta"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # id de negocio (n del Excel)
    n: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mes: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    fecha_alerta: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    local: Mapped[str] = mapped_column(String(200), default="", nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    cliente: Mapped[str] = mapped_column(String(200), default="", nullable=False, index=True)
    contacto: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    estado_gestion: Mapped[str] = mapped_column(String(80), default="Sin gestión", nullable=False)
    clasificacion: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    asesor: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
