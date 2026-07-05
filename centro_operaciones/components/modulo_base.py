"""
Interfaz base para módulos del Centro de Operaciones.

Cada módulo implementa `render()` y opcionalmente expone metadatos
para el registro central (registry.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd
import streamlit as st

from centro_operaciones.components.export_excel import boton_exportar_excel
from centro_operaciones.components.layout import render_header, render_kpis, render_toolbar
from centro_operaciones.components.respuesta_ia import render_panel_desde_fila
from services.respuesta_ia_service import RespuestaIAService


@dataclass
class ModuloMeta:
    id: str
    label: str
    descripcion: str
    icono: str = ""
    orden: int = 0


class ModuloOperaciones(ABC):
    """Clase base opcional para módulos con patrón uniforme."""

    meta: ModuloMeta

    @abstractmethod
    def cargar_datos(self) -> pd.DataFrame:
        ...

    @abstractmethod
    def render_contenido(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renderiza tabla/contenido. Retorna df visible para exportar."""
        ...

    def contexto_ia_desde_fila(self, fila: dict) -> dict:
        return RespuestaIAService.contexto_desde_fila(
            fila,
            self.meta.id,
        )

    def render_panel_ia(self, fila: dict, *, key_prefix: str | None = None) -> None:
        render_panel_desde_fila(
            fila,
            self.meta.id,
            titulo_modulo=self.meta.label.replace("🛡️ ", "").replace("📡 ", "").strip(),
            key_prefix=key_prefix or self.meta.id,
        )

    def render_export(self, df: pd.DataFrame, nombre_archivo: str) -> None:
        boton_exportar_excel(
            df,
            nombre_archivo=nombre_archivo,
            titulo_hoja=self.meta.label[:31],
            key=f"export_{self.meta.id}",
        )

    def render(self) -> None:
        render_header(self.meta.label, self.meta.descripcion)
        df = self.cargar_datos()
        df_visible = self.render_contenido(df)
        render_toolbar(titulo="Exportar y acciones")
        self.render_export(df_visible, f"{self.meta.id}_export.xlsx")


def render_modulo_estandar(
    *,
    meta: ModuloMeta,
    df: pd.DataFrame,
    kpis: list[tuple[str, str | int]] | None = None,
    columna_sel: str = "id",
    formato_sel: Callable | None = None,
    nombre_export: str | None = None,
    contexto_extra_fn: Callable[[dict], dict] | None = None,
) -> None:
    """
    Atajo para módulos stub: header + KPIs + tabla + export + panel IA.
    """
    render_header(meta.label, meta.descripcion)
    if kpis:
        render_kpis(kpis)

    st.dataframe(df, use_container_width=True, hide_index=True)

    render_toolbar()
    boton_exportar_excel(
        df,
        nombre_archivo=nombre_export or f"{meta.id}.xlsx",
        titulo_hoja=meta.id[:31],
        key=f"export_{meta.id}",
    )

    st.divider()
    st.markdown("#### 🤖 Asistente IA del módulo")

    if df.empty:
        st.info("Sin registros para generar diálogo.")
        return

    ids = df[columna_sel].tolist()
    sel = st.selectbox(
        "Seleccionar caso",
        ids,
        format_func=formato_sel or (lambda i: str(i)),
        key=f"sel_{meta.id}",
    )
    fila = df[df[columna_sel] == sel].iloc[0].to_dict()
    ctx_base = {**fila}
    if contexto_extra_fn:
        ctx_base = contexto_extra_fn(ctx_base)

    render_panel_desde_fila(
        ctx_base,
        meta.id,
        titulo_modulo=meta.label,
        key_prefix=meta.id,
    )