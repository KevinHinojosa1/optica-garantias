from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("numero_factura", name="uq_clientes_numero_factura"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cedula: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tienda: Mapped[str] = mapped_column(String(150), nullable=False, index=True, default="Sin asignar")
    producto: Mapped[str] = mapped_column(String(300), nullable=False)
    tipo_producto: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_factura: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    numero_factura: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    tiene_ola_plus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    codigo_descuento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    porcentaje_descuento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)