"""
Registro central de módulos — Centro de Operaciones Óptica Los Andes.

Cada entrada define: id, etiqueta sidebar, descripción y función render().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from centro_operaciones.modulos.alertas_telegram import render as render_alertas
from centro_operaciones.modulos.codigos_descuento import render as render_descuentos
from centro_operaciones.modulos.garantias import render as render_garantias
from centro_operaciones.modulos.ivr import render as render_ivr
from centro_operaciones.modulos.leadbox import render as render_leadbox
from centro_operaciones.modulos.proteccion_datos import render as render_proteccion
from centro_operaciones.modulos.reclamos_activos import render as render_reclamos
from centro_operaciones.modulos.reportes_matrices import render as render_reportes
from centro_operaciones.modulos.whatsapp_business import render as render_whatsapp


@dataclass(frozen=True)
class ModuloRegistro:
    id: str
    label: str
    descripcion: str
    render: Callable[[], None]
    orden: int = 0


MODULOS: list[ModuloRegistro] = [
    ModuloRegistro(
        id="garantias",
        label="🛡️ Garantías",
        descripcion="Gestión de garantías, clientes, historial y análisis (FastAPI).",
        render=render_garantias,
        orden=1,
    ),
    ModuloRegistro(
        id="alertas_telegram",
        label="📡 Alertas Telegram",
        descripcion="Matriz editable de alertas, clasificación y seguimiento.",
        render=render_alertas,
        orden=2,
    ),
    ModuloRegistro(
        id="reclamos_activos",
        label="📋 Reclamos Activos",
        descripcion="Casos abiertos de reclamos y seguimiento posventa.",
        render=render_reclamos,
        orden=3,
    ),
    ModuloRegistro(
        id="leadbox",
        label="📥 LeadBox",
        descripcion="Bandeja de leads entrantes y conversión a oportunidades.",
        render=render_leadbox,
        orden=4,
    ),
    ModuloRegistro(
        id="whatsapp_business",
        label="💬 WhatsApp Business",
        descripcion="Cola de mensajes, priorización y respuestas asistidas.",
        render=render_whatsapp,
        orden=5,
    ),
    ModuloRegistro(
        id="ivr",
        label="📞 1800 / IVR",
        descripcion="Verificaciones IVR por tienda y línea 1800.",
        render=render_ivr,
        orden=6,
    ),
    ModuloRegistro(
        id="codigos_descuento",
        label="🏷️ Códigos de Descuento",
        descripcion="Validación y registro de códigos promocionales.",
        render=render_descuentos,
        orden=7,
    ),
    ModuloRegistro(
        id="proteccion_datos",
        label="🔒 Protección de Datos",
        descripcion="Solicitudes ARCO, consentimientos y trazabilidad.",
        render=render_proteccion,
        orden=8,
    ),
    ModuloRegistro(
        id="reportes_matrices",
        label="📊 Reportes y Matrices",
        descripcion="Matrices consolidadas y reportes operativos.",
        render=render_reportes,
        orden=9,
    ),
]


def labels_sidebar() -> list[str]:
    return [m.label for m in sorted(MODULOS, key=lambda x: x.orden)]


def modulo_por_label(label: str) -> ModuloRegistro | None:
    for m in MODULOS:
        if m.label == label:
            return m
    return None