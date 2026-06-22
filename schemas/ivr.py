from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IvrRegistroRequest(BaseModel):
    tienda_id: str
    funciona: bool
    comentario: str = ""
    verificado_por: str = "Sistema"


class IvrActualizarRequest(BaseModel):
    funciona: bool
    comentario: str = ""
    verificado_por: str = "Sistema"


class IvrRegistroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tienda_id: str
    tienda_nombre: str
    ciudad: str
    funciona: bool
    comentario: Optional[str]
    verificado_por: str
    fecha: str
    semana: str
    created_at: datetime
    google_sheets_ok: bool = False
    google_sheets_mensaje: str = ""


class IvrTiendaEstado(BaseModel):
    tienda_id: str
    tienda_nombre: str
    ciudad: str
    funciona: Optional[bool] = None
    comentario: Optional[str] = None
    verificado_at: Optional[str] = None
    verificado_por: Optional[str] = None
    semana: str