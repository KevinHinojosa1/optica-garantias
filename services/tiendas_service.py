import json
import unicodedata
from datetime import date
from pathlib import Path

TIENDAS_FILE = Path(__file__).parent.parent / "data" / "tiendas.json"


class TiendasService:
    _cache: list[dict] | None = None

    ALIAS_MAP: dict[str, str] = {
        "cci": "Cci 1",
        "recreo": "Recreo 1",
        "bosque": "Bosque 1",
        "scala": "Scala Shopping",
        "condado": "Condado Shopping",
        "el jardin osh": "Mall el Jardin Sgh",
    }

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
        if not nombre or not nombre.strip():
            return None

        norm_query = cls._normalizar(nombre)

        # 0. Check ALIAS_MAP for known abbreviations/shortcuts
        if norm_query in cls.ALIAS_MAP:
            target_norm = cls._normalizar(cls.ALIAS_MAP[norm_query])
            for tienda in cls.cargar_tiendas():
                if cls._normalizar(tienda["nombre"]) == target_norm:
                    return tienda

        common_words = {"mall", "paseo", "shopping", "centro", "ola", "sgh", "osh"}

        def get_tokens(text: str) -> list[str]:
            norm = cls._normalizar(text)
            return [t for t in "".join(c if c.isalnum() else " " for c in norm).split() if t]

        def get_meaningful_tokens(tokens: list[str]) -> list[str]:
            meaningful = [t for t in tokens if t not in common_words]
            return meaningful if meaningful else tokens

        query_tokens = get_tokens(nombre)
        if not query_tokens:
            return None

        tiendas = cls.cargar_tiendas()

        # b. Check exact match first
        for tienda in tiendas:
            if cls._normalizar(tienda["nombre"]) == norm_query:
                return tienda

        # c. Check if all words of the query appear in the store name (or vice versa)
        query_set = set(query_tokens)
        for tienda in tiendas:
            store_tokens = get_tokens(tienda["nombre"])
            store_set = set(store_tokens)
            if query_set and store_set:
                if query_set.issubset(store_set) or store_set.issubset(query_set):
                    if len(query_set & store_set) / len(query_set) >= 0.5:
                        return tienda

        # d & e. Token-overlap score with meaningful words and >= 50% match requirement
        query_meaningful = get_meaningful_tokens(query_tokens)
        query_m_set = set(query_meaningful)

        best_tienda = None
        max_overlap = 0
        best_match_ratio = 0.0

        for tienda in tiendas:
            store_tokens = get_tokens(tienda["nombre"])
            store_meaningful = get_meaningful_tokens(store_tokens)
            store_m_set = set(store_meaningful)

            overlap = len(query_m_set & store_m_set)
            match_ratio = overlap / len(query_m_set) if query_m_set else 0

            if match_ratio >= 0.5:
                if overlap > max_overlap or (overlap == max_overlap and match_ratio > best_match_ratio):
                    max_overlap = overlap
                    best_match_ratio = match_ratio
                    best_tienda = tienda

        return best_tienda


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