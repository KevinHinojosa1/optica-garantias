from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ContactoEnvio(BaseModel):
    nombre: str = ""
    telefono: str = ""
    local: str = ""
    producto: str = ""
    orden: str = ""
    cedula: str = ""
    factura: str = ""
    email_tienda: str = ""
    fecha_reprogramada: str = ""
    fecha_anterior: str = ""
    hora: str = ""
    motivo: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerarEnviosRequest(BaseModel):
    plantilla: str = Field(default="", min_length=0)
    asesor: str = ""
    incluir_pie: bool = True
    fecha_reprogramada: str = ""
    fecha_anterior: str = ""
    hora: str = ""
    motivo: str = ""
    registrar_log: bool = True
    contactos: list[ContactoEnvio]


class EnvioGenerado(BaseModel):
    indice: int
    nombre: str
    telefono: str
    telefono_limpio: str = ""
    local: str = ""
    producto: str = ""
    factura: str = ""
    orden: str = ""
    email_tienda: str = ""
    mensaje: str = ""
    mensaje_cliente: str = ""
    mensaje_tienda: str = ""
    wa_link: str = ""
    wa_link_cliente: str = ""
    wa_link_tienda: str = ""
    valido: bool
    error: Optional[str] = None


class CorreoLocalGenerado(BaseModel):
    local: str
    asunto: str
    cuerpo: str
    email_tienda: str = ""
    total_matriz: int = 0
    filas: list[dict[str, Any]] = Field(default_factory=list)


class GenerarEnviosResponse(BaseModel):
    total: int
    validos: int
    invalidos: int
    items: list[EnvioGenerado]
    correos: list[CorreoLocalGenerado] = Field(default_factory=list)
    resumen_dia: dict[str, Any] = Field(default_factory=dict)
    plantillas: dict[str, str] = Field(default_factory=dict)


class SubirExcelEnviosResponse(BaseModel):
    total: int
    columnas_detectadas: list[str]
    contactos: list[ContactoEnvio]
    advertencias: list[str] = Field(default_factory=list)


class WhatsAppConfigResponse(BaseModel):
    business_api_activa: bool
    phone_number_id: str = ""
    api_version: str = ""
    smtp_activo: bool = False
    smtp_host: str = ""
    smtp_from: str = ""


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


class MarcarEnviadoRequest(BaseModel):
    local: str = ""
    nombre: str = ""
    producto: str = ""
    factura: str = ""
    telefono: str = ""
    canal: str = "cliente"
    estado: str = "Mensaje enviado"


class EnviarCorreoRequest(BaseModel):
    local: str
    asunto: str
    cuerpo: str
    email_tienda: str = ""
