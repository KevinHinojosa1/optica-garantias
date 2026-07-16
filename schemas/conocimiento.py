from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConocimientoCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=250)
    categoria: str = "politica_oficial"
    contenido: str = Field(..., min_length=10)
    tags: str = ""
    fuente: str = "Óptica Los Andes"
    prioridad: int = Field(default=50, ge=1, le=100)
    activo: bool = True


class ConocimientoUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=3, max_length=250)
    categoria: Optional[str] = None
    contenido: Optional[str] = Field(default=None, min_length=10)
    tags: Optional[str] = None
    fuente: Optional[str] = None
    prioridad: Optional[int] = Field(default=None, ge=1, le=100)
    activo: Optional[bool] = None


class ConocimientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    categoria: str
    contenido: str
    tags: str
    imagen_path: Optional[str] = None
    imagen_url: Optional[str] = None
    fuente: str
    prioridad: int
    activo: bool
    created_at: datetime
    updated_at: datetime


class ConocimientoListResponse(BaseModel):
    total: int
    activos: int
    items: list[ConocimientoResponse]
    categorias: list[dict[str, str]]