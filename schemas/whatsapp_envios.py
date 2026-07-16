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
    fecha_reprogramada: str = ""
    fecha_anterior: str = ""
    hora: str = ""
    motivo: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerarEnviosRequest(BaseModel):
    plantilla: str = Field(..., min_length=5)
    asesor: str = ""
    incluir_pie: bool = True
    fecha_reprogramada: str = ""
    fecha_anterior: str = ""
    hora: str = ""
    motivo: str = ""
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


class WhatsAppConfigResponse(BaseModel):
    business_api_activa: bool
    phone_number_id: str = ""
    api_version: str = ""


class EnviarBusinessItem(BaseModel):
    indice: int = 0
    telefono_limpio: str
    mensaje: str = Field(..., min_length=1)


class EnviarBusinessRequest(BaseModel):
    item: EnviarBusinessItem


class EnviarBusinessLoteRequest(BaseModel):
    items: list[EnviarBusinessItem] = Field(..., min_length=1)


class EnviarBusinessResponse(BaseModel):
    ok: bool
    message_id: str = ""
    telefono: str = ""
    indice: int = 0
    error: Optional[str] = None


class EnviarBusinessLoteResponse(BaseModel):
    enviados: int
    fallidos: int
    resultados: list[dict[str, Any]]