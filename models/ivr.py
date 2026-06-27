from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class IvrVerificacion(Base):
    __tablename__ = "ivr_verificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tienda_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    tienda_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(80), nullable=False)
    funciona: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    comentario_auditoria: Mapped[str | None] = mapped_column(Text, nullable=True)
    verificado_por: Mapped[str] = mapped_column(String(100), nullable=False, default="Sistema")
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    semana: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)