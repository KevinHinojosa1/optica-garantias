from typing import Any, Optional

from pydantic import BaseModel, Field


class FichaCliente(BaseModel):
    id: Optional[int] = None
    historial_id: Optional[int] = None
    fuente: str = "manual"
    nombre: str = ""
    cedula: str = ""
    telefono: str = ""
    tienda: str = ""
    producto: str = ""
    tipo_producto: str = ""
    numero_factura: str = ""
    fecha_factura: str = ""
    fecha_entrega: Optional[str] = None
    tiene_ola_plus: bool = False
    codigo_descuento: Optional[int] = None
    porcentaje_descuento: Optional[int] = None
    dias_desde_factura: Optional[int] = None
    dentro_garantia: Optional[bool] = None
    estado_garantia: Optional[str] = None
    veredicto: Optional[str] = None
    motivo: Optional[str] = None
    fundamento: Optional[str] = None
    confianza: Optional[int] = None
    fecha_prometida: Optional[str] = None
    nueva_fecha: Optional[str] = None
    motivo_operativo: Optional[str] = None


class BuscarFuentesItem(BaseModel):
    tipo: str
    id: int
    titulo: str
    subtitulo: str


class BuscarFuentesResponse(BaseModel):
    resultados: list[BuscarFuentesItem]


class ArmarWhatsAppRequest(BaseModel):
    cuerpo: str
    asesor: str = ""
    ficha: FichaCliente


class ArmarWhatsAppResponse(BaseModel):
    mensaje: str
    wa_link: str
    incluye_ficha: bool = False


class GenerarRespuestaRequest(BaseModel):
    mensaje_cliente: str = Field(..., min_length=2)
    asesor: str = ""
    ficha: FichaCliente
    escenario: str = ""
    contexto_adicional: str = ""


class GenerarRespuestaResponse(BaseModel):
    mensaje_voz: str
    mensaje_whatsapp: str
    wa_link: str
    generado_por: str


class DialogoLinea(BaseModel):
    actor: str
    texto: str


class GenerarDialogoRequest(BaseModel):
    escenario_id: str = Field(..., min_length=1)
    grupo_id: str = ""
    asesor: str = ""
    ficha: FichaCliente = Field(default_factory=FichaCliente)
    canal: str = "voz"
    fase: str = "saludo"
    contexto_adicional: str = ""


class GenerarDialogoResponse(BaseModel):
    dialogo: list[DialogoLinea]
    mensaje_voz: str
    mensaje_whatsapp: str
    wa_link: str = ""
    generado_por: str
    nota_asesor: str = ""