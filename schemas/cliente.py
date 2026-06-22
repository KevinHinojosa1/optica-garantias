from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    nombre: str
    cedula: str
    telefono: str
    tienda: str
    producto: str
    tipo_producto: str
    fecha_factura: date
    numero_factura: str
    fecha_entrega: Optional[date] = None
    tiene_ola_plus: bool = False
    codigo_descuento: Optional[int] = None
    porcentaje_descuento: Optional[int] = None


class DescuentoUpdate(BaseModel):
    codigo_descuento: Optional[int] = None
    porcentaje_descuento: Optional[int] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # codigo_descuento y porcentaje_descuento heredados de ClienteBase
    dias_desde_factura: int
    dentro_garantia: bool
    estado_garantia: str
    es_duplicado: bool = False
    created_at: datetime


class ClienteListResponse(BaseModel):
    items: list[ClienteResponse]
    total: int
    page: int
    pages: int
    per_page: int


class ImportResult(BaseModel):
    total_filas: int
    registros_insertados: int
    errores: int
    duplicados: int = 0
    detalle_errores: list[str]
    detalle_duplicados: list[str] = []
    archivo: str | None = None
    registros_eliminados: int = 0
    modo: str | None = None