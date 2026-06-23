import json
import unicodedata
from datetime import date
from pathlib import Path

TIENDAS_FILE = Path(__file__).parent.parent / "data" / "tiendas.json"


class TiendasService:
    _cache: list[dict] | None = None

    @classmethod
    def _normalizar(cls, texto: str) -> str:
        texto = unicodedata.normalize("NFKD", texto.lower().strip())
        return "".join(c for c in texto if not unicodedata.combining(c))

    @classmethod
    def cargar_tiendas(cls) -> list[dict]:
        if cls._cache is None:
            with open(TIENDAS_FILE, encoding="utf-8") as f:
                cls._cache = json.load(f)
        return cls._cache

    @classmethod
    def listar(cls) -> list[dict]:
        return cls.cargar_tiendas()

    @classmethod
    def buscar_por_nombre(cls, nombre: str) -> dict | None:
        if not nombre:
            return None
        norm = cls._normalizar(nombre)
        for tienda in cls.cargar_tiendas():
            if cls._normalizar(tienda["nombre"]) == norm:
                return tienda
            if norm in cls._normalizar(tienda["nombre"]) or cls._normalizar(tienda["nombre"]) in norm:
                return tienda
        return None

    @classmethod
    def obtener(cls, tienda_id: str) -> dict | None:
        for tienda in cls.cargar_tiendas():
            if tienda["id"] == tienda_id:
                return tienda
        return None

    @classmethod
    def resolver_para_cliente(cls, tienda_nombre: str) -> dict:
        tienda = cls.buscar_por_nombre(tienda_nombre)
        if tienda:
            return tienda
        central = cls.obtener("central-call-center")
        return {
            **central,
            "nombre": tienda_nombre or "Tienda no identificada",
            "nota": "Tienda no encontrada en catálogo — enviado a Call Center Central",
        }

    @classmethod
    def nombres_validos(cls) -> list[str]:
        return [t["nombre"] for t in cls.cargar_tiendas() if t["id"] != "central-call-center"]

    @classmethod
    def validar_tienda(cls, nombre: str) -> bool:
        if not nombre or not nombre.strip():
            return False
        return cls.buscar_por_nombre(nombre) is not None

    @classmethod
    def nombres_por_ciudad(cls, ciudad: str) -> list[str]:
        if not ciudad or not ciudad.strip():
            return []
        ciudad_norm = cls._normalizar(ciudad)
        return [
            t["nombre"]
            for t in cls.cargar_tiendas()
            if t["id"] != "central-call-center" and cls._normalizar(t["ciudad"]) == ciudad_norm
        ]

    @classmethod
    def ciudad_de_tienda(cls, nombre: str) -> str | None:
        tienda = cls.buscar_por_nombre(nombre)
        return tienda["ciudad"] if tienda else None

    @classmethod
    def dia_ivr_laboral(cls, fecha: date | None = None) -> int | None:
        """Lunes=1 … Viernes=5. Fin de semana devuelve None."""
        f = fecha or date.today()
        if f.weekday() > 4:
            return None
        return f.weekday() + 1

    @classmethod
    def listar_ivr(cls, dia: int | None = None) -> list[dict]:
        tiendas = [t for t in cls.listar() if t.get("id") != "central-call-center"]
        if dia is None:
            return tiendas
        return [t for t in tiendas if t.get("dia_ivr") == dia]