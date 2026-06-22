from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class HistorialConsulta(Base):
    __tablename__ = "historial_consultas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    veredicto: Mapped[str] = mapped_column(String(50), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fundamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    confianza: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asesor: Mapped[str] = mapped_column(String(100), nullable=False)
    mensaje_enviado: Mapped[str | None] = mapped_column(Text, nullable=True)
    codigo_descuento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    porcentaje_descuento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imagen_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    cliente = relationship("Cliente", backref="consultas")