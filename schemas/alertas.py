"""Esquemas API — módulo Alertas Telegram."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AlertasFiltrosRequest(BaseModel):
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    locales: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    clasificaciones: list[str] = Field(default_factory=list)
    estados: list[str] = Field(default_factory=list)
    contesto: list[str] = Field(default_factory=list)
    texto: str = ""
    solo_pendientes: bool = False


class AlertasListResponse(BaseModel):
    total: int
    filtrado: int
    pendientes: int
    filas: list[dict[str, Any]]


class AlertasKpisResponse(BaseModel):
    total_filtrado: int
    sin_gestion: int
    resueltos: int
    contesto_si: int
    pendientes: int


class AlertasGuardarRequest(BaseModel):
    filas: list[dict[str, Any]]


class AlertasClasificarRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


class AlertasGraficosResponse(BaseModel):
    tendencia: dict[str, Any]
    top_problemas: dict[str, Any]
    heatmap: dict[str, Any]
    heatmap_mes_local: dict[str, Any]
    donut: dict[str, Any]


class AlertasSubirExcelResponse(BaseModel):
    ok: bool
    total: int
    nuevas: int
    pendientes: int
    ids_pendientes_ia: list[int] = Field(default_factory=list)