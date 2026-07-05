"""Constantes del Centro de Operaciones — Alertas Telegram."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ALERTAS_CSV = DATA_DIR / "alertas_telegram.csv"
ALERTAS_PARQUET = DATA_DIR / "alertas_telegram.parquet"

COLUMNAS_EDITABLES = [
    "llamada_cliente",
    "contesto",
    "solucion",
    "clasificacion",
    "estado_gestion",
    "asesor",
]

COLUMNAS_ORDEN = [
    "id",
    "fecha_alerta",
    "local",
    "area",
    "problema",
    "descripcion",
    "cliente",
    "telefono",
    "mensaje_telegram",
    "llamada_cliente",
    "contesto",
    "solucion",
    "clasificacion",
    "estado_gestion",
    "asesor",
    "dialogo_ia",
    "canal_dialogo",
    "clasificado_por",
]

OPCIONES_LLAMADA = ["Pendiente", "Sí", "No"]
OPCIONES_CONTESTO = ["Pendiente", "Sí", "No", "No contesta"]
OPCIONES_ESTADO = ["Sin gestión", "En proceso", "Resuelto"]
OPCIONES_CLASIFICACION = [
    "Retraso entrega",
    "Garantía / cambio",
    "Calidad producto",
    "Atención en tienda",
    "Precio / facturación",
    "Adaptación visual",
    "Información / consulta",
    "Reclamo laboratorio",
    "Otro",
]

AREAS = ["Ventas", "Laboratorio", "Postventa", "Logística", "Administración", "Call Center"]

REGLAS_CLASIFICACION: list[tuple[str, list[str]]] = [
    ("Retraso entrega", ["retraso", "demora", "tarde", "no lleg", "esperando", "plazo"]),
    ("Garantía / cambio", ["garant", "cambio", "devol", "reemplaz", "defectu"]),
    ("Calidad producto", ["rayad", "roto", "mal estado", "defecto", "no ve", "adapt"]),
    ("Atención en tienda", ["mala atención", "groser", "asesor", "trato", "servicio"]),
    ("Precio / facturación", ["precio", "factur", "cobr", "descuento", "promo"]),
    ("Adaptación visual", ["mareo", "no enfoca", "adaptación", "dolor cabeza", "visión"]),
    ("Información / consulta", ["inform", "horario", "ubic", "consulta", "pregunt"]),
    ("Reclamo laboratorio", ["laboratorio", "montaje", "luna", "progresiv"]),
]