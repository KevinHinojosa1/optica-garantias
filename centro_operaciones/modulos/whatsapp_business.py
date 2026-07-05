"""Módulo WhatsApp Business — cola de mensajes."""

from __future__ import annotations

import pandas as pd

from centro_operaciones.components.modulo_base import ModuloMeta, render_modulo_estandar

META = ModuloMeta(
    id="whatsapp_business",
    label="💬 WhatsApp Business",
    descripcion="Cola de mensajes entrantes y tiempos de espera.",
)


def _datos() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 101, "cliente": "Pedro Vega", "telefono": "0994445566", "local": "Ambato",
         "mensaje": "¿Cuándo llegan mis lentes?", "espera_min": 45, "prioridad": "Alta", "estado": "Pendiente"},
        {"id": 102, "cliente": "Lucía Mendoza", "telefono": "0985556677", "local": "Riobamba",
         "mensaje": "Necesito factura de mi compra", "espera_min": 20, "prioridad": "Media", "estado": "En atención"},
        {"id": 103, "cliente": "Jorge Salinas", "telefono": "0976667788", "local": "Manta",
         "mensaje": "Mis gafas llegaron rayadas", "espera_min": 90, "prioridad": "Alta", "estado": "Pendiente"},
    ])


def render() -> None:
    df = _datos()
    render_modulo_estandar(
        meta=META,
        df=df,
        kpis=[
            ("En cola", len(df)),
            ("Alta prioridad", (df["prioridad"] == "Alta").sum()),
            ("Espera prom. (min)", int(df["espera_min"].mean())),
        ],
        columna_sel="id",
        formato_sel=lambda i: f"#{i} — {df.loc[df['id']==i,'cliente'].iloc[0]}",
        nombre_export="whatsapp_business.xlsx",
        contexto_extra_fn=lambda f: {
            "id": f["id"],
            "cliente": f["cliente"],
            "telefono": f["telefono"],
            "local": f["local"],
            "comentario_cliente": f["mensaje"],
            "problema": f["mensaje"],
            "descripcion": f"Espera: {f.get('espera_min', '')} min · Prioridad: {f.get('prioridad', '')}",
        },
    )