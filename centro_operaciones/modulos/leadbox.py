"""Módulo LeadBox — bandeja de leads entrantes."""

from __future__ import annotations

import pandas as pd

from centro_operaciones.components.modulo_base import ModuloMeta, render_modulo_estandar

META = ModuloMeta(
    id="leadbox",
    label="📥 LeadBox",
    descripcion="Leads entrantes desde web, redes y campañas.",
)


def _datos() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": "LB-101", "cliente": "Sofía Herrera", "telefono": "0998877665", "local": "Quito Norte",
         "origen": "Facebook Ads", "interes": "Lentes progresivos", "estado": "Nuevo", "dias": 0},
        {"id": "LB-102", "cliente": "Miguel Castro", "telefono": "0987766554", "local": "Cuenca",
         "origen": "Google", "interes": "Examen visual gratis", "estado": "Contactado", "dias": 1},
        {"id": "LB-103", "cliente": "Valentina Cruz", "telefono": "0976655443", "local": "Guayaquil Sur",
         "origen": "Instagram", "interes": "Promo 2x1", "estado": "Cita agendada", "dias": 2},
    ])


def render() -> None:
    df = _datos()
    render_modulo_estandar(
        meta=META,
        df=df,
        kpis=[
            ("Nuevos", (df["estado"] == "Nuevo").sum()),
            ("Contactados", (df["estado"] == "Contactado").sum()),
            ("Citas", (df["estado"] == "Cita agendada").sum()),
        ],
        columna_sel="id",
        formato_sel=lambda i: f"{i} — {df.loc[df['id']==i,'cliente'].iloc[0]}",
        nombre_export="leadbox.xlsx",
        contexto_extra_fn=lambda f: {
            **f,
            "descripcion": f"Interés: {f.get('interes', '')} · Origen: {f.get('origen', '')}",
            "problema": f.get("interes", ""),
        },
    )