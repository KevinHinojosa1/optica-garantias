from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ConocimientoItem(Base):
    """Entrada de la base de conocimiento oficial para veredictos Claude."""

    __tablename__ = "conocimiento_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="politica_oficial")
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    imagen_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
    fuente: Mapped[str] = mapped_column(String(200), default="Óptica Los Andes", nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)