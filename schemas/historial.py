from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HistorialCreate(BaseModel):
    cliente_id: Optional[int] = None
    cliente_nombre: str
    veredicto: str
    motivo: Optional[str] = None
    fundamento: Optional[str] = None
    confianza: Optional[int] = None
    asesor: str
    mensaje_enviado: Optional[str] = None
    codigo_descuento: Optional[int] = None
    porcentaje_descuento: Optional[int] = None
    imagen_path: Optional[str] = None


class HistorialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: Optional[int]
    cliente_nombre: str
    veredicto: str
    motivo: Optional[str]
    fundamento: Optional[str]
    confianza: Optional[int]
    asesor: str
    mensaje_enviado: Optional[str]
    codigo_descuento: Optional[int]
    porcentaje_descuento: Optional[int]
    imagen_path: Optional[str]
    created_at: datetime