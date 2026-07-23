from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CuadernoNotaCreate(BaseModel):
    titulo: str = Field(default="Sin título", max_length=250)
    contenido: str = ""
    emoji: str = "📝"
    color: str = "amber"
    categoria: str = "general"
    tags: str = ""
    fijada: bool = False
    autor: str = ""


class CuadernoNotaUpdate(BaseModel):
    titulo: Optional[str] = None
    contenido: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None
    categoria: Optional[str] = None
    tags: Optional[str] = None
    fijada: Optional[bool] = None
    autor: Optional[str] = None


class CuadernoAdjuntoOut(BaseModel):
    id: int
    nombre: str
    url: str
    mime: str


class CuadernoNotaOut(BaseModel):
    id: int
    titulo: str
    contenido: str
    emoji: str
    color: str
    categoria: str
    tags: list[str] = Field(default_factory=list)
    tags_raw: str = ""
    fijada: bool = False
    autor: str = ""
    created_at: str = ""
    updated_at: str = ""
    adjuntos: list[CuadernoAdjuntoOut] = Field(default_factory=list)


class CuadernoListResponse(BaseModel):
    total: int
    notas: list[dict[str, Any]]
    secciones: list[dict[str, Any]] = Field(default_factory=list)
    categorias: list[dict[str, Any]]
    colores: list[str]
