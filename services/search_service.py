import unicodedata

from sqlalchemy import ColumnElement, func, or_

from models.cliente import Cliente

ACCENT_MAP = (
    ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n"),
    ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u"), ("Ü", "u"), ("Ñ", "n"),
)


class SearchService:
    @staticmethod
    def normalizar_texto(texto: str) -> str:
        texto = unicodedata.normalize("NFKD", texto.lower().strip())
        return "".join(c for c in texto if not unicodedata.combining(c))

    @classmethod
    def columna_normalizada(cls, columna):
        expr = func.lower(columna)
        for origen, destino in ACCENT_MAP:
            expr = func.replace(expr, origen, destino)
        return expr

    @classmethod
    def filtro_busqueda(cls, termino: str) -> ColumnElement:
        term = f"%{cls.normalizar_texto(termino)}%"
        campos = (
            Cliente.nombre,
            Cliente.cedula,
            Cliente.numero_factura,
            Cliente.telefono,
            Cliente.tienda,
            Cliente.producto,
        )
        return or_(*[cls.columna_normalizada(c).like(term) for c in campos])