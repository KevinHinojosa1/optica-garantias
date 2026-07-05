"""Módulo Reclamos Activos — Centro de Operaciones."""

from __future__ import annotations

import pandas as pd

from centro_operaciones.components.modulo_base import ModuloMeta, render_modulo_estandar

META = ModuloMeta(
    id="reclamos_activos",
    label="📋 Reclamos Activos",
    descripcion="Casos abiertos de reclamos y seguimiento posventa.",
)


def _datos() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1, "cliente": "María López", "telefono": "0991112233", "local": "Quito Centro",
         "problema": "Lentes con error de graduación", "estado": "Abierto", "dias_abierto": 5,
         "comentario": "No ve bien con los lentes nuevos", "calificacion": "2/5"},
        {"id": 2, "cliente": "Carlos Ruiz", "telefono": "0982223344", "local": "Cuenca Centro",
         "problema": "Garantía pendiente", "estado": "En revisión", "dias_abierto": 12,
         "comentario": "Esperando respuesta del laboratorio", "calificacion": "1/5"},
        {"id": 3, "cliente": "Ana Torres", "telefono": "0973334455", "local": "Guayaquil Norte",
         "problema": "Devolución solicitada", "estado": "Abierto", "dias_abierto": 3,
         "comentario": "Quiere devolver la montura", "calificacion": "2/5"},
    ])


def render() -> None:
    df = _datos()
    render_modulo_estandar(
        meta=META,
        df=df,
        kpis=[
            ("Abiertos", (df["estado"] == "Abierto").sum()),
            ("En revisión", (df["estado"] == "En revisión").sum()),
            ("Prom. días", f"{df['dias_abierto'].mean():.0f}"),
        ],
        columna_sel="id",
        formato_sel=lambda i: f"#{i} — {df.loc[df['id']==i,'cliente'].iloc[0]}",
        nombre_export="reclamos_activos.xlsx",
        contexto_extra_fn=lambda f: {
            **f,
            "descripcion": f.get("comentario", ""),
            "estado_gestion": f.get("estado", ""),
            "historial": f"Días abierto: {f.get('dias_abierto', '')}",
            "calificacion": f.get("calificacion", ""),
        },
    )