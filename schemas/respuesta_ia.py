from typing import Any, Optional

from pydantic import BaseModel, Field


class DialogoLinea(BaseModel):
    actor: str
    texto: str


class ContextoCaso(BaseModel):
    """Contexto estándar reutilizable en cualquier módulo del Centro de Operaciones."""

    modulo: str = Field(..., description="alertas_telegram | reclamos_activos | whatsapp | scripts | otro")
    caso_id: Optional[str] = None
    cliente_nombre: str = "{cliente}"
    telefono: str = "{telefono}"
    email: str = ""
    local: str = ""
    asesor: str = ""
    comentario_cliente: str = ""
    historial: str = ""
    calificacion: str = ""
    problema: str = ""
    descripcion: str = ""
    clasificacion: str = ""
    estado: str = ""
    solucion_actual: str = ""
    contexto_extra: str = ""
    canal: str = "whatsapp"  # whatsapp | correo | ambos


class GenerarRespuestaIARequest(BaseModel):
    contexto: ContextoCaso
    titulo_modulo: str = ""
    guardar_como_plantilla: bool = False
    nombre_plantilla: str = ""


class GenerarRespuestaIAResponse(BaseModel):
    dialogo: list[DialogoLinea]
    mensaje_whatsapp: str
    mensaje_correo: str
    asunto_correo: str = ""
    mensaje_voz: str = ""
    nota_asesor: str = ""
    wa_link: str = ""
    generado_por: str
    plantilla_id: Optional[str] = None


class GuardarPlantillaRequest(BaseModel):
    nombre: str = Field(..., min_length=2)
    modulo: str = ""
    mensaje_whatsapp: str = ""
    mensaje_correo: str = ""
    asunto_correo: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlantillaRespuestaIA(BaseModel):
    id: str
    nombre: str
    modulo: str
    mensaje_whatsapp: str
    mensaje_correo: str
    asunto_correo: str
    creada_en: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlantillasListResponse(BaseModel):
    plantillas: list[PlantillaRespuestaIA]