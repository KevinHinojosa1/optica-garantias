CODIGOS_VALIDOS = list(range(10, 55, 5))  # 10, 15, 20, ..., 50


class DescuentoService:
    @staticmethod
    def validar(codigo: int | None, porcentaje: int | None) -> tuple[int | None, int | None]:
        if codigo is None and porcentaje is None:
            return None, None
        if codigo is not None:
            if codigo not in CODIGOS_VALIDOS:
                raise ValueError(f"Código de descuento inválido. Use valores: {CODIGOS_VALIDOS}")
        if porcentaje is not None:
            if porcentaje < 10 or porcentaje > 50:
                raise ValueError("El porcentaje aplicado debe estar entre 10% y 50%.")
            if codigo is not None and porcentaje > codigo:
                raise ValueError(
                    f"El porcentaje aplicado ({porcentaje}%) no puede superar el código ({codigo}%)."
                )
        return codigo, porcentaje

    @staticmethod
    def texto_reporte(codigo: int | None, porcentaje: int | None) -> str:
        if codigo is None and porcentaje is None:
            return "Sin descuento registrado"
        partes = []
        if codigo is not None:
            partes.append(f"Código autorizado: {codigo}%")
        if porcentaje is not None:
            partes.append(f"Aplicado: {porcentaje}%")
        return " · ".join(partes)