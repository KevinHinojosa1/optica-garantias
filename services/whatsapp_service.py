from datetime import datetime
from urllib.parse import quote

from services.descuento_service import DescuentoService
from services.garantia_service import GarantiaService
from services.tiendas_service import TiendasService


class WhatsAppService:
    @staticmethod
    def limpiar_telefono(telefono: str) -> str:
        digits = "".join(c for c in telefono if c.isdigit())
        if digits.startswith("593"):
            return digits
        if digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 9:
            return f"593{digits}"
        return digits

    @staticmethod
    def normalizar_mensaje_whatsapp(mensaje: str) -> str:
        """Normaliza el texto para que emojis y tildes lleguen bien a WhatsApp (UTF-8)."""
        if mensaje is None:
            return ""
        if not isinstance(mensaje, str):
            mensaje = str(mensaje)
        # NFC: forma canónica Unicode (evita glifos rotos / rombos en móviles)
        import unicodedata

        texto = unicodedata.normalize("NFC", mensaje)
        # Separadores tipográficos que en algunos dispositivos salen como rombo
        texto = (
            texto.replace("\u2501", "-")  # ━
            .replace("\u2500", "-")  # ─
            .replace("\u2014", "-")  # —
            .replace("\u2013", "-")  # –
            .replace("\ufeff", "")
            .replace("\u200b", "")
        )
        # Unificar saltos de línea
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        return texto

    @staticmethod
    def generar_enlace(telefono: str, mensaje: str) -> str:
        """Genera enlace wa.me con texto codificado en UTF-8 (emojis correctos en iOS/Android)."""
        numero = WhatsAppService.limpiar_telefono(telefono)
        texto = WhatsAppService.normalizar_mensaje_whatsapp(mensaje)
        # safe='' codifica todo lo no alfanumérico; encoding UTF-8 explícito
        texto_q = quote(texto, safe="", encoding="utf-8", errors="strict")
        # api.whatsapp.com es más estable con Unicode que solo wa.me en algunos clientes
        return f"https://api.whatsapp.com/send?phone={numero}&text={texto_q}"

    @classmethod
    def _encabezado_interno(cls, cliente: dict, tienda: dict) -> str:
        return (
            f"🏥 *ÓPTICA LOS ANDES — REPORTE DE GARANTÍA*\n"
            f"📍 *Tienda:* {tienda.get('nombre', 'N/D')}\n"
            f"🏙️ *Ciudad:* {tienda.get('ciudad', 'N/D')}\n"
            f"📌 *Dirección:* {tienda.get('direccion', 'N/D')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Cliente:* {cliente.get('nombre', 'N/D')}\n"
            f"🪪 *Cédula:* {cliente.get('cedula', 'N/D')}\n"
            f"📞 *Tel. cliente:* {cliente.get('telefono', 'N/D')}\n"
            f"🧾 *Factura:* {cliente.get('numero_factura', 'N/D')} | {cliente.get('fecha_factura', 'N/D')}\n"
            f"👓 *Producto:* {cliente.get('producto', 'N/D')}\n"
            f"📦 *Tipo:* {cliente.get('tipo_producto', 'N/D')}\n"
            f"🛡️ *OLA Plus:* {'Sí' if cliente.get('tiene_ola_plus') else 'No'}\n"
            f"⏱️ *Días desde factura:* {cliente.get('dias_desde_factura', 'N/D')}\n"
            f"📊 *Estado garantía:* {cliente.get('estado_garantia', 'N/D')}\n"
            f"🏷️ *Descuento:* {DescuentoService.texto_reporte(cliente.get('codigo_descuento'), cliente.get('porcentaje_descuento'))}\n"
        )

    @classmethod
    def _pie_interno(cls, asesor: str = "") -> str:
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        pie = f"━━━━━━━━━━━━━━━━━━━━\n🕐 *Reporte generado:* {fecha}"
        if asesor:
            pie += f"\n👨‍💼 *Asesor:* {asesor}"
        pie += "\n— Sistema de Garantías Óptica Los Andes"
        return pie

    @classmethod
    def mensaje_pre_cargado(cls, cliente: dict, asesor: str = "") -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        return (
            cls._encabezado_interno(cliente, tienda)
            + f"\n📋 *Tipo de solicitud:* Consulta de garantía\n"
            f"📝 *Detalle:* Cliente contactó por garantía. Revisar expediente y coordinar atención en tienda.\n"
            + cls._pie_interno(asesor)
        )

    @classmethod
    def mensaje_aprobado(cls, cliente: dict, dano: str, periodo: str, asesor: str = "") -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        return (
            cls._encabezado_interno(cliente, tienda)
            + f"\n✅ *VEREDICTO: APLICA GARANTÍA*\n"
            f"🔧 *Daño cubierto:* {dano}\n"
            f"📅 *Período aplicable:* {periodo}\n"
            f"📌 *Acción requerida:* Coordinar revisión técnica en tienda. Solicitar factura original al cliente.\n"
            + cls._pie_interno(asesor)
        )

    @classmethod
    def mensaje_rechazado(cls, cliente: dict, dano: str, exclusion: str, asesor: str = "") -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        return (
            cls._encabezado_interno(cliente, tienda)
            + f"\n❌ *VEREDICTO: NO APLICA GARANTÍA*\n"
            f"🔧 *Daño detectado:* {dano}\n"
            f"📋 *Fundamento:* {exclusion}\n"
            f"📌 *Acción requerida:* Asesorar al cliente sobre opciones de reparación o reposición. Call Center: 1800 678422.\n"
            + cls._pie_interno(asesor)
        )

    @classmethod
    def mensaje_gafas_fuera_plazo(cls, cliente: dict, asesor: str = "") -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        info = GarantiaService.es_gafas_fuera_plazo(cliente["tipo_producto"], cliente["fecha_factura"])
        dias = info["dias_habiles"] if info else 0
        return (
            cls._encabezado_interno(cliente, tienda)
            + f"\n⚠️ *VEREDICTO: CAMBIO DE GAFAS NO PROCEDE*\n"
            f"📅 *Fecha compra:* {cliente['fecha_factura']}\n"
            f"📊 *Días hábiles transcurridos:* {dias} (máximo permitido: 3)\n"
            f"📋 *Política:* Cambio de modelo solo hasta 3 días hábiles desde la compra.\n"
            f"📌 *Acción requerida:* Informar al cliente que el cambio no aplica bajo esta política.\n"
            + cls._pie_interno(asesor)
        )

    @classmethod
    def mensaje_imagen_no_clara(cls, cliente: dict, asesor: str = "") -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        return (
            cls._encabezado_interno(cliente, tienda)
            + f"\n🔍 *VEREDICTO: IMAGEN NO CLARA*\n"
            f"📸 *Detalle:* La foto enviada no permite clasificar el daño con certeza.\n"
            f"📌 *Acción requerida:* Solicitar al cliente una segunda foto con buena iluminación, "
            f"mostrando el producto completo y el área dañada de cerca.\n"
            + cls._pie_interno(asesor)
        )

    @classmethod
    def generar_desde_analisis(cls, cliente: dict, analisis: dict, asesor: str = "") -> str:
        veredicto = analisis.get("veredicto", "").upper()
        motivo = analisis.get("motivo", "daño no especificado")
        fundamento = analisis.get("fundamento", "Política de garantía Óptica Los Andes")
        confianza = analisis.get("confianza", "")

        if veredicto == "IMAGEN NO CLARA":
            msg = cls.mensaje_imagen_no_clara(cliente, asesor)
        else:
            gafas_info = GarantiaService.es_gafas_fuera_plazo(
                cliente["tipo_producto"], cliente["fecha_factura"]
            )
            if gafas_info and not gafas_info["aplica_cambio"] and "gafa" in cliente["tipo_producto"].lower():
                msg = cls.mensaje_gafas_fuera_plazo(cliente, asesor)
            elif veredicto == "APLICA":
                periodo = GarantiaService.evaluar_estado_general(
                    cliente["fecha_factura"], cliente.get("tiene_ola_plus", False)
                )["periodo_aplicable"]
                msg = cls.mensaje_aprobado(cliente, motivo, periodo, asesor)
            else:
                msg = cls.mensaje_rechazado(cliente, motivo, fundamento, asesor)

        if confianza and veredicto != "IMAGEN NO CLARA":
            msg = msg.replace(
                "━━━━━━━━━━━━━━━━━━━━\n🕐",
                f"📊 *Confianza:* {confianza}%\n━━━━━━━━━━━━━━━━━━━━\n🕐",
                1,
            )
        return msg

    @classmethod
    def agregar_enlace_pdf(cls, mensaje: str, pdf_url: str, consulta_id: int) -> str:
        bloque = (
            f"\n\n📄 *INFORME PDF — Consulta #{consulta_id}*\n"
            f"Descargar informe completo con foto y veredicto:\n"
            f"{pdf_url}\n"
            f"_Abra el enlace, descargue el PDF y compártalo en el grupo si lo necesita._"
        )
        return mensaje.rstrip() + bloque

    @staticmethod
    def _valor_real(val) -> bool:
        if val is None:
            return False
        s = str(val).strip()
        return bool(s) and s not in ("N/D", "…", "-", "—", "None")

    @classmethod
    def resolver_tienda_scripts(cls, tienda_nombre: str) -> dict:
        if not cls._valor_real(tienda_nombre):
            return {}
        tienda = TiendasService.resolver_para_cliente(tienda_nombre)
        if tienda.get("id") == "central-call-center":
            return {}
        return tienda

    @classmethod
    def encabezado_scripts(cls, cliente: dict) -> str:
        tienda = cls.resolver_tienda_scripts(cliente.get("tienda", ""))
        if not cls._valor_real(cliente.get("nombre")):
            return ""

        bloques: list[str] = ["💬 *ÓPTICA LOS ANDES — ATENCIÓN AL CLIENTE*"]

        if cls._valor_real(tienda.get("nombre")):
            bloques.append(f"📍 *Tienda:* {tienda['nombre']}")
        if cls._valor_real(tienda.get("ciudad")):
            bloques.append(f"🏙️ *Ciudad:* {tienda['ciudad']}")
        if cls._valor_real(tienda.get("direccion")):
            bloques.append(f"📌 *Dirección:* {tienda['direccion']}")

        datos_cliente: list[str] = []
        if cls._valor_real(cliente.get("nombre")):
            datos_cliente.append(f"👤 *Cliente:* {cliente['nombre']}")
        if cls._valor_real(cliente.get("cedula")):
            datos_cliente.append(f"🪪 *Cédula:* {cliente['cedula']}")
        if cls._valor_real(cliente.get("telefono")):
            datos_cliente.append(f"📞 *Teléfono:* {cliente['telefono']}")
        if cls._valor_real(cliente.get("numero_factura")) or cls._valor_real(cliente.get("fecha_factura")):
            factura = cliente.get("numero_factura", "")
            fecha = cliente.get("fecha_factura", "")
            datos_cliente.append(f"🧾 *Factura:* {factura} | {fecha}".rstrip(" | "))
        if cls._valor_real(cliente.get("producto")):
            datos_cliente.append(f"👓 *Producto:* {cliente['producto']}")
        if cls._valor_real(cliente.get("tipo_producto")):
            datos_cliente.append(f"📦 *Tipo:* {cliente['tipo_producto']}")
        if cliente.get("tiene_ola_plus"):
            datos_cliente.append("🛡️ *OLA Plus:* Sí")
        if cls._valor_real(cliente.get("dias_desde_factura")):
            datos_cliente.append(f"⏱️ *Días desde factura:* {cliente['dias_desde_factura']}")
        if cls._valor_real(cliente.get("estado_garantia")):
            datos_cliente.append(f"📊 *Estado garantía:* {cliente['estado_garantia']}")
        desc = DescuentoService.texto_reporte(
            cliente.get("codigo_descuento"), cliente.get("porcentaje_descuento")
        )
        if desc != "Sin descuento registrado":
            datos_cliente.append(f"🏷️ *Descuento:* {desc}")
        if cls._valor_real(cliente.get("veredicto")):
            datos_cliente.append(f"📋 *Veredicto:* {cliente['veredicto']}")

        if datos_cliente:
            bloques.append("━━━━━━━━━━━━━━━━━━━━")
            bloques.extend(datos_cliente)

        if len(bloques) <= 1 and not datos_cliente:
            return ""

        return "\n".join(bloques)

    @classmethod
    def pie_scripts(cls, asesor: str = "") -> str:
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        pie = f"━━━━━━━━━━━━━━━━━━━━\n🕐 *Mensaje enviado:* {fecha}"
        if cls._valor_real(asesor):
            pie += f"\n👨‍💼 *Asesor:* {asesor}"
        pie += "\n💙 *Gracias por confiar en Óptica Los Andes*"
        pie += "\n_Ante cualquier consulta, estamos para servirle._"
        return pie

    @classmethod
    def ficha_lista_para_whatsapp(cls, cliente: dict) -> bool:
        if not cls._valor_real(cliente.get("nombre")):
            return False
        campos = (
            cliente.get("tienda"),
            cliente.get("cedula"),
            cliente.get("numero_factura"),
            cliente.get("producto"),
            cliente.get("telefono"),
        )
        return sum(1 for c in campos if cls._valor_real(c)) >= 2

    @classmethod
    def mensaje_scripts_completo(cls, cliente: dict, cuerpo: str, asesor: str = "") -> str:
        cuerpo_limpio = cuerpo.strip()
        partes = []
        if cls.ficha_lista_para_whatsapp(cliente):
            encabezado = cls.encabezado_scripts(cliente)
            if encabezado:
                partes.append(encabezado)
        partes.append(cuerpo_limpio)
        partes.append(cls.pie_scripts(asesor))
        return "\n\n".join(p for p in partes if p)

    @classmethod
    def encabezado_atencion(cls, cliente: dict) -> str:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        return cls._encabezado_interno(cliente, tienda)

    @classmethod
    def mensaje_atencion_completo(cls, cliente: dict, cuerpo: str, asesor: str = "") -> str:
        return cls.mensaje_scripts_completo(cliente, cuerpo, asesor)

    @classmethod
    def enlace_grupo_apoyo(cls, cliente: dict, mensaje: str) -> tuple[str, dict]:
        tienda = TiendasService.resolver_para_cliente(cliente.get("tienda", ""))
        numero = tienda.get("whatsapp_grupo", "5931800678422")
        return cls.generar_enlace(numero, mensaje), tienda