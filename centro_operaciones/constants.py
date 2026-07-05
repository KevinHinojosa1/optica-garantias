"""Constantes del Centro de Operaciones — Alertas Telegram."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ALERTAS_EXCEL = DATA_DIR / "ALERTAS_TELEGRAM_2026.xlsx"
ALERTAS_EXCEL_HOJA = "GENERAL"
ALERTAS_CSV = DATA_DIR / "alertas_telegram.csv"
ALERTAS_PARQUET = DATA_DIR / "alertas_telegram.parquet"

# Columnas editables en la matriz de gestión diaria
COLUMNAS_EDITABLES = [
    "llamada_cliente",
    "contesto",
    "observacion_gestion",
    "solucion",
    "clasificacion",
    "estado_gestion",
    "asesor",
    "quien_llama",
    "correos_disculpa",
    "dialogo_ia",
    "canal_dialogo",
]

COLUMNAS_ORDEN = [
    "id",
    "n",
    "mes",
    "fecha_alerta",
    "canal",
    "local",
    "area",
    "optometra",
    "asesor",
    "momento",
    "calificacion",
    "pregunta",
    "responde",
    "comentario",
    "cliente",
    "cedula_id",
    "contacto",
    "correos_disculpa",
    "llamada_cliente",
    "contesto",
    "observacion_gestion",
    "solucion",
    "quien_llama",
    "clasificacion",
    "estado_gestion",
    "dialogo_ia",
    "canal_dialogo",
    "clasificado_por",
    # alias compatibilidad IA / filtros
    "telefono",
    "mensaje_telegram",
    "problema",
    "descripcion",
]

# Encabezados para exportación Excel (hoja GENERAL)
COLUMNAS_EXCEL_EXPORTE = [
    ("n", "n"),
    ("mes", "Mes"),
    ("fecha_alerta", "Fecha"),
    ("canal", "Canal"),
    ("local", "Local"),
    ("area", "Área"),
    ("optometra", "Optómetra"),
    ("asesor", "Asesor"),
    ("momento", "Momento"),
    ("calificacion", "Calificación"),
    ("pregunta", "Pregunta"),
    ("responde", "Responde"),
    ("comentario", "Comentario"),
    ("cliente", "CLIENTE"),
    ("cedula_id", "ID"),
    ("contacto", "CONTACTO"),
    ("correos_disculpa", "Correos disculpa"),
    ("llamada_cliente", "llamada cliente"),
    ("contesto", "Contestó"),
    ("observacion_gestion", "OBSERVACIÓN / GESTIÓN DE LLAMADAS"),
    ("solucion", "SOLUCIÓN"),
    ("quien_llama", "quien llama"),
    ("clasificacion", "CLASIFICACION"),
    ("estado_gestion", "Estado gestión"),
    ("dialogo_ia", "Diálogo IA"),
]

OPCIONES_LLAMADA = ["Pendiente", "Sí", "No", "si", "no"]
OPCIONES_CONTESTO = ["Pendiente", "Sí", "No", "No contesta", "si", "no"]
OPCIONES_ESTADO = ["Sin gestión", "En proceso", "Resuelto", "Pendiente llamada"]
OPCIONES_CLASIFICACION = [
    "Demora entrega",
    "Garantía / OLA sin informar",
    "Errores de medidas / calidad",
    "Atención deficiente",
    "Falta de explicación",
    "Cobros extras",
    "Asesoría / información",
    "Control de calidad",
    "Tiempo de entrega",
    "Atención al cliente",
    "Otro",
    "Sin clasificar",
]

AREAS = ["Ventas", "Optometría", "Laboratorio", "Postventa", "Logística", "Administración", "Call Center"]

REGLAS_CLASIFICACION: list[tuple[str, list[str]]] = [
    ("Demora entrega", ["demora", "retraso", "tarde", "esperando", "plazo", "dos semanas", "demor"]),
    ("Tiempo de entrega", ["tiempo de entrega", "entrega", "no lleg", "plazo entrega"]),
    ("Garantía / OLA sin informar", ["garant", "ola plus", "ola sin", "sin informar garant", "devol"]),
    ("Errores de medidas / calidad", ["medida", "gradu", "incorrect", "luna", "cambiadas", "error", "defecto", "rayad", "no ve", "progresiv"]),
    ("Atención deficiente", ["mala atención", "groser", "pésima", "mal rato", "discut", "deficiente", "trato"]),
    ("Falta de explicación", ["explic", "informacion incompleta", "no se otorg", "poca asesor", "pocas recomend"]),
    ("Cobros extras", ["cobr", "precio", "factur", "extra", "devuelven el dinero", "nota de crédito"]),
    ("Asesoría / información", ["asesor", "recomend", "consulta", "inform"]),
    ("Control de calidad", ["calidad", "verific", "control"]),
    ("Atención al cliente", ["atencion al cliente", "atención al cliente", "servicio"]),
]

MAPEO_EXCEL = {
    "n": "n",
    "Mes": "mes",
    "Fecha": "fecha_alerta",
    "Canal": "canal",
    "Local": "local",
    "Área ": "area",
    "Área": "area",
    "Optómetra ": "optometra",
    "Optómetra": "optometra",
    "Asesor": "asesor",
    "Momento": "momento",
    "Calificación ": "calificacion",
    "Calificación": "calificacion",
    "Pregunta": "pregunta",
    "Responde": "responde",
    "Comentario": "comentario",
    "CLIENTE ": "cliente",
    "CLIENTE": "cliente",
    "ID": "cedula_id",
    "CONTACTO ": "contacto",
    "CONTACTO": "contacto",
    "Correos disculpa": "correos_disculpa",
    "llamada cliente": "llamada_cliente",
    "Contestó": "contesto",
    "OBSERVACIÓN / GESTIÓN DE LLAMADAS": "observacion_gestion",
    "SOLUCIÓN": "solucion",
    "quien llama": "quien_llama",
    "CLASIFICACION": "clasificacion",
}