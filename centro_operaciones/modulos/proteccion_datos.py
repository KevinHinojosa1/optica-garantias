"""Módulo Protección de Datos — solicitudes ARCO y consentimientos."""

from __future__ import annotations

import pandas as pd

from centro_operaciones.components.modulo_base import ModuloMeta, render_modulo_estandar

META = ModuloMeta(
    id="proteccion_datos",
    label="🔒 Protección de Datos",
    descripcion="Solicitudes de acceso, rectificación, cancelación y oposición (ARCO).",
)


def _datos() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": "PD-01", "cliente": "Fernando Arias", "telefono": "0991122334", "tipo": "Acceso",
         "estado": "En revisión", "fecha": "2026-07-01", "plazo_dias": 12},
        {"id": "PD-02", "cliente": "Patricia Núñez", "telefono": "0982233445", "tipo": "Rectificación",
         "estado": "Resuelto", "fecha": "2026-06-28", "plazo_dias": 15},
        {"id": "PD-03", "cliente": "Roberto Salgado", "telefono": "0973344556", "tipo": "Cancelación",
         "estado": "Pendiente", "fecha": "2026-07-03", "plazo_dias": 10},
    ])


def render() -> None:
    df = _datos()
    render_modulo_estandar(
        meta=META,
        df=df,
        kpis=[
            ("Solicitudes", len(df)),
            ("Pendientes", (df["estado"] == "Pendiente").sum()),
            ("En revisión", (df["estado"] == "En revisión").sum()),
        ],
        columna_sel="id",
        formato_sel=lambda i: f"{i} — {df.loc[df['id']==i,'cliente'].iloc[0]} ({df.loc[df['id']==i,'tipo'].iloc[0]})",
        nombre_export="proteccion_datos.xlsx",
        contexto_extra_fn=lambda f: {
            **f,
            "problema": f"Solicitud {f.get('tipo', '')} de datos personales",
            "descripcion": f"Estado: {f.get('estado', '')} · Plazo legal: {f.get('plazo_dias', '')} días",
        },
    )