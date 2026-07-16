from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ContactoEnvio(BaseModel):
    nombre: str = ""
    telefono: str
    local: str = ""
    producto: str = ""
    cedula: str = ""
    factura: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerarEnviosRequest(BaseModel):
    plantilla: str = Field(..., min_length=5)
    asesor: str = ""
    incluir_pie: bool = True
    contactos: list[ContactoEnvio]


class EnvioGenerado(BaseModel):
    indice: int
    nombre: str
    telefono: str
    telefono_limpio: str
    mensaje: str
    wa_link: str
    valido: bool
    error: Optional[str] = None


class GenerarEnviosResponse(BaseModel):
    total: int
    validos: int
    invalidos: int
    items: list[EnvioGenerado]


class SubirExcelEnviosResponse(BaseModel):
    total: int
    columnas_detectadas: list[str]
    contactos: list[ContactoEnvio]
    advertencias: list[str] = Field(default_factory=list)