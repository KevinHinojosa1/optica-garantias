from datetime import date, datetime, timedelta


class GarantiaService:
    @staticmethod
    def _as_date(value: date | str) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    TIPOS_PRODUCTO = {
        "lente oftalmico",
        "lente oftálmico",
        "armazon",
        "armazón",
        "gafa",
        "lente de contacto",
    }

    @staticmethod
    def dias_habiles_desde(fecha_inicio: date, fecha_fin: date | None = None) -> int:
        fin = fecha_fin or date.today()
        if fin < fecha_inicio:
            return 0
        dias = 0
        actual = fecha_inicio
        while actual < fin:
            if actual.weekday() < 5:
                dias += 1
            actual += timedelta(days=1)
        return dias

    @staticmethod
    def dias_desde_factura(fecha_factura: date) -> int:
        return (date.today() - fecha_factura).days

    @classmethod
    def evaluar_estado_general(cls, fecha_factura: date | str, tiene_ola_plus: bool) -> dict:
        fecha = cls._as_date(fecha_factura)
        dias = cls.dias_desde_factura(fecha)
        limite = 360 if tiene_ola_plus else 365
        dentro = dias <= limite
        return {
            "dias_desde_factura": dias,
            "dentro_garantia": dentro,
            "estado_garantia": "DENTRO DE GARANTÍA" if dentro else "FUERA DE GARANTÍA",
            "periodo_aplicable": f"{limite} días ({'OLA Plus' if tiene_ola_plus else 'estándar'})",
        }

    @classmethod
    def periodo_para_dano(cls, tipo_dano: str, tipo_producto: str, tiene_ola_plus: bool) -> int:
        tipo = tipo_producto.lower().strip()
        dano = tipo_dano.lower()

        if tiene_ola_plus:
            return 360

        if "gafa" in tipo and ("cambio" in dano or "modelo" in dano):
            return 3  # días hábiles
        if "adaptación" in dano or "medida" in dano:
            return 30
        if "ar" in dano or "anti-reflejo" in dano or "antireflejo" in dano:
            return 365
        if "borde" in dano or "despostill" in dano or "perforación" in dano:
            return 180
        if "lente de contacto" in tipo:
            return 1
        return 365

    @classmethod
    def es_gafas_fuera_plazo(cls, tipo_producto: str, fecha_factura: date | str) -> dict | None:
        tipo = tipo_producto.lower().strip()
        if "gafa" not in tipo:
            return None
        fecha = cls._as_date(fecha_factura)
        dias_habiles = cls.dias_habiles_desde(fecha)
        if dias_habiles > 3:
            return {
                "aplica_cambio": False,
                "dias_habiles": dias_habiles,
                "fecha_compra": fecha.isoformat(),
            }
        return {
            "aplica_cambio": True,
            "dias_habiles": dias_habiles,
            "fecha_compra": fecha.isoformat(),
        }