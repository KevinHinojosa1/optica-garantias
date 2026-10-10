"""Pruebas del módulo Alertas Telegram (servicio, persistencia y API)."""

import io

import pandas as pd

from models.alerta import AlertaTelegram
from services.alertas_db_service import _parse_fecha
from services.alertas_service import AlertasService


def test_listar_y_kpis(alertas_env):
    res = AlertasService.listar({})
    assert res["total"] == 3 and res["filtrado"] == 3
    k = AlertasService.kpis({"locales": ["CCI 2"]})
    assert k["total_filtrado"] == 1


def test_filtro_fecha_hasta_no_incluye_dia_siguiente(alertas_env):
    res = AlertasService.listar({"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-02"})
    assert [f["id"] for f in res["filas"]] == [1]


def test_parse_fecha_iso_no_invierte_dia_mes():
    assert _parse_fecha("2026-01-02T00:00:00").isoformat() == "2026-01-02"
    assert _parse_fecha("2026-01-02").isoformat() == "2026-01-02"
    assert _parse_fecha("02/01/2026").isoformat() == "2026-01-02"


def test_ids_duplicados_no_rompen_persistencia_bd(alertas_env):
    ds = alertas_env["ds"]
    filas = pd.DataFrame([
        {"id": 10, "n": 10, "local": "A", "comentario": "x"},
        {"id": 10, "n": 10, "local": "B", "comentario": "y"},
    ])
    ds.guardar_alertas(filas)
    with alertas_env["Session"]() as db:
        assert db.query(AlertaTelegram).count() == 2


def test_guardar_filas_persiste_en_bd(alertas_env):
    AlertasService.guardar_filas([{"id": 2, "solucion": "Se llamó y se resolvió"}])
    with alertas_env["Session"]() as db:
        assert "Se llamó y se resolvió" in db.get(AlertaTelegram, 2).payload_json


def test_guardar_filas_solo_columnas_editables(alertas_env):
    AlertasService.guardar_filas([{"id": 1, "cliente": "HACK", "cedula_id": "000", "solucion": "ok"}])
    fila = next(f for f in AlertasService.listar({})["filas"] if f["id"] == 1)
    assert fila["cliente"] == "Cliente A"
    assert fila["solucion"] == "ok"


def test_api_fecha_invalida_responde_422(client):
    r = client.get("/api/alertas", params={"fecha_desde": "no-es-fecha"})
    assert r.status_code == 422


def test_api_clasificar_ia_sin_api_key_usa_reglas(client):
    r = client.post("/api/alertas/clasificar-ia", json={"ids": [1, 2]})
    assert r.status_code == 200, r.text
    assert r.json()["clasificadas"] == 2


def test_api_importar_csv_invalido_no_borra_datos(client):
    r = client.post(
        "/api/alertas/importar",
        files={"archivo": ("x.csv", io.BytesIO(b"foo,bar\n1,2\n"), "text/csv")},
    )
    assert r.status_code == 422
    assert AlertasService.listar({})["total"] == 3


def test_api_ingresar_alerta(client):
    r = client.post("/api/alertas/ingresar", json={"local": "QUICENTRO", "comentario": "Demora"})
    assert r.status_code == 200
    assert r.json()["id"] == 4
    assert AlertasService.listar({})["total"] == 4


def test_exportar_excel_neutraliza_formulas(alertas_env):
    AlertasService.guardar_filas([{"id": 1, "solucion": "=HYPERLINK(\"http://evil\",\"x\")"}])
    data = AlertasService.exportar_excel({})
    df = pd.read_excel(io.BytesIO(data), sheet_name="GENERAL")
    assert not df.astype(str).apply(lambda c: c.str.startswith("=")).any().any()


def test_ia_resultados_se_asignan_por_id(alertas_env, monkeypatch):
    import asyncio

    import centro_operaciones.services.clasificacion_ia_alertas as mod

    class FakeResp:
        status_code = 200

        def json(self):
            return {"content": [{"text": '{"resultados": ['
                                 '{"id": 2, "clasificacion": "Cobros extras / valores no solicitados / precio", "justificacion": "b", "solucion": "s2"},'
                                 '{"id": 1, "clasificacion": "Demora en entrega / no avisan cuando está listo", "justificacion": "a", "solucion": "s1"}]}'}]}

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): ...
        async def post(self, *a, **k): return FakeResp()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(mod.settings, "anthropic_api_key", "test")
    out = asyncio.run(mod._clasificar_lote_claude([{"id": 1}, {"id": 2}]))
    por_id = {r["id"]: r for r in out}
    assert por_id[1]["solucion"] == "s1"
    assert por_id[2]["solucion"] == "s2"


def test_lecturas_no_reescriben_archivos(alertas_env):
    csv = alertas_env["ds"].ALERTAS_CSV
    AlertasService.listar({})
    antes = csv.stat().st_mtime_ns
    AlertasService.listar({})
    AlertasService.kpis({})
    assert csv.stat().st_mtime_ns == antes
