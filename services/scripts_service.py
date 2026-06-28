import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from models.cliente import Cliente
from models.historial import HistorialConsulta
from services.descuento_service import DescuentoService
from services.garantia_service import GarantiaService
from services.search_service import SearchService
from services.tiendas_service import TiendasService
from services.whatsapp_service import WhatsAppService

RUTA_SCRIPTS = Path(__file__).resolve().parent.parent / "data" / "scripts_atencion.json"


class ScriptsService:
    @staticmethod
    def cargar() -> dict:
        with open(RUTA_SCRIPTS, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def personalizar(texto: str, variables: dict[str, str]) -> str:
        resultado = texto
        for clave, valor in variables.items():
            resultado = resultado.replace(f"{{{clave}}}", valor or f"[{clave}]")
        return resultado

    @classmethod
    def listar_grupos(cls) -> list[dict]:
        return cls.cargar().get("grupos", [])

    @staticmethod
    def _fecha_str(val) -> str:
        if not val:
            return ""
        if isinstance(val, date):
            return val.strftime("%d/%m/%Y")
        return str(val)

    @classmethod
    def cliente_a_ficha(cls, cliente: Cliente, fuente: str = "atencion") -> dict:
        estado = GarantiaService.evaluar_estado_general(
            cliente.fecha_factura, cliente.tiene_ola_plus
        )
        return {
            "id": cliente.id,
            "historial_id": None,
            "fuente": fuente,
            "nombre": cliente.nombre,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono,
            "tienda": cliente.tienda,
            "producto": cliente.producto,
            "tipo_producto": cliente.tipo_producto,
            "numero_factura": cliente.numero_factura,
            "fecha_factura": cls._fecha_str(cliente.fecha_factura),
            "fecha_entrega": cls._fecha_str(cliente.fecha_entrega),
            "tiene_ola_plus": cliente.tiene_ola_plus,
            "codigo_descuento": cliente.codigo_descuento,
            "porcentaje_descuento": cliente.porcentaje_descuento,
            "dias_desde_factura": estado["dias_desde_factura"],
            "dentro_garantia": estado["dentro_garantia"],
            "estado_garantia": estado["estado_garantia"],
            "veredicto": None,
            "motivo": None,
            "fundamento": None,
            "confianza": None,
        }

    @classmethod
    def historial_a_ficha(cls, db: Session, registro: HistorialConsulta) -> dict:
        if registro.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == registro.cliente_id).first()
            if cliente:
                ficha = cls.cliente_a_ficha(cliente, fuente="historial")
                ficha["historial_id"] = registro.id
                ficha["veredicto"] = registro.veredicto
                ficha["motivo"] = registro.motivo
                ficha["fundamento"] = registro.fundamento
                ficha["confianza"] = registro.confianza
                if registro.codigo_descuento is not None:
                    ficha["codigo_descuento"] = registro.codigo_descuento
                if registro.porcentaje_descuento is not None:
                    ficha["porcentaje_descuento"] = registro.porcentaje_descuento
                return ficha

        return {
            "id": registro.cliente_id,
            "historial_id": registro.id,
            "fuente": "historial",
            "nombre": registro.cliente_nombre,
            "cedula": "",
            "telefono": "",
            "tienda": "",
            "producto": "",
            "tipo_producto": "",
            "numero_factura": "",
            "fecha_factura": "",
            "fecha_entrega": None,
            "tiene_ola_plus": False,
            "codigo_descuento": registro.codigo_descuento,
            "porcentaje_descuento": registro.porcentaje_descuento,
            "dias_desde_factura": None,
            "dentro_garantia": None,
            "estado_garantia": None,
            "veredicto": registro.veredicto,
            "motivo": registro.motivo,
            "fundamento": registro.fundamento,
            "confianza": registro.confianza,
        }

    @classmethod
    def ficha_desde_cliente(cls, db: Session, cliente_id: int) -> dict | None:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return None
        return cls.cliente_a_ficha(cliente)

    @classmethod
    def ficha_desde_historial(cls, db: Session, historial_id: int) -> dict | None:
        registro = db.query(HistorialConsulta).filter(HistorialConsulta.id == historial_id).first()
        if not registro:
            return None
        return cls.historial_a_ficha(db, registro)

    @classmethod
    def buscar_fuentes(cls, db: Session, q: str, limit: int = 12) -> list[dict]:
        termino = q.strip()
        if len(termino) < 2:
            return []

        clientes = (
            db.query(Cliente)
            .filter(SearchService.filtro_busqueda(termino))
            .order_by(Cliente.nombre)
            .limit(limit)
            .all()
        )
        resultados = [
            {
                "tipo": "atencion",
                "id": c.id,
                "titulo": c.nombre,
                "subtitulo": f"{c.cedula} · {c.tienda} · Fact. {c.numero_factura}",
            }
            for c in clientes
        ]

        if len(resultados) < limit:
            restante = limit - len(resultados)
            hist = (
                db.query(HistorialConsulta)
                .filter(HistorialConsulta.cliente_nombre.ilike(f"%{termino}%"))
                .order_by(HistorialConsulta.created_at.desc())
                .limit(restante)
                .all()
            )
            ids_cli = {r["id"] for r in resultados if r["tipo"] == "atencion"}
            for h in hist:
                if h.cliente_id and h.cliente_id in ids_cli:
                    continue
                resultados.append(
                    {
                        "tipo": "historial",
                        "id": h.id,
                        "titulo": h.cliente_nombre,
                        "subtitulo": (
                            f"Consulta #{h.id} · {h.veredicto} · "
                            f"{h.created_at.strftime('%d/%m/%Y %H:%M')}"
                        ),
                    }
                )
        return resultados

    @classmethod
    def ficha_a_cliente_dict(cls, ficha: dict) -> dict:
        return {
            "nombre": (ficha.get("nombre") or "").strip(),
            "cedula": (ficha.get("cedula") or "").strip(),
            "telefono": (ficha.get("telefono") or "").strip(),
            "tienda": (ficha.get("tienda") or "").strip(),
            "producto": (ficha.get("producto") or "").strip(),
            "tipo_producto": (ficha.get("tipo_producto") or "").strip(),
            "numero_factura": (ficha.get("numero_factura") or "").strip(),
            "fecha_factura": (ficha.get("fecha_factura") or "").strip(),
            "fecha_entrega": ficha.get("fecha_entrega"),
            "tiene_ola_plus": bool(ficha.get("tiene_ola_plus")),
            "codigo_descuento": ficha.get("codigo_descuento"),
            "porcentaje_descuento": ficha.get("porcentaje_descuento"),
            "dias_desde_factura": ficha.get("dias_desde_factura"),
            "estado_garantia": (ficha.get("estado_garantia") or "").strip(),
            "veredicto": (ficha.get("veredicto") or "").strip(),
        }

    @classmethod
    def extraer_cuerpo_whatsapp(cls, plantilla: str) -> str:
        cuerpo = plantilla
        if "{ficha}" in cuerpo:
            partes = cuerpo.split("{ficha}", 1)
            cuerpo = partes[1] if len(partes) > 1 else cuerpo
        if "{pie}" in cuerpo:
            cuerpo = cuerpo.split("{pie}")[0]
        return cuerpo.strip()

    @classmethod
    def armar_whatsapp(cls, cuerpo: str, ficha: dict, asesor: str = "") -> dict:
        cliente_dict = cls.ficha_a_cliente_dict(ficha)
        cuerpo_personalizado = cls.personalizar(cuerpo, cls.ficha_a_variables(ficha, asesor))
        mensaje = WhatsAppService.mensaje_scripts_completo(
            cliente_dict, cuerpo_personalizado, asesor
        )
        telefono = ficha.get("telefono", "")
        wa_link = WhatsAppService.generar_enlace(telefono, mensaje) if telefono else ""
        tienda = WhatsAppService.resolver_tienda_scripts(ficha.get("tienda", ""))
        return {
            "mensaje": mensaje,
            "wa_link": wa_link,
            "tienda": tienda,
            "incluye_ficha": WhatsAppService.ficha_lista_para_whatsapp(cliente_dict),
        }

    @classmethod
    def ficha_a_variables(cls, ficha: dict, asesor: str = "") -> dict[str, str]:
        tienda_info = WhatsAppService.resolver_tienda_scripts(ficha.get("tienda", ""))
        return {
            "asesor": asesor or "…",
            "cliente": ficha.get("nombre") or "…",
            "cedula": ficha.get("cedula") or "…",
            "telefono": ficha.get("telefono") or "…",
            "tienda": ficha.get("tienda") or tienda_info.get("nombre") or "…",
            "ciudad": tienda_info.get("ciudad") or "…",
            "direccion": tienda_info.get("direccion") or "…",
            "producto": ficha.get("producto") or "…",
            "tipo_producto": ficha.get("tipo_producto") or "…",
            "factura": ficha.get("numero_factura") or "…",
            "fecha_factura": ficha.get("fecha_factura") or "…",
            "fecha_prometida": ficha.get("fecha_prometida") or "…",
            "nueva_fecha": ficha.get("nueva_fecha") or "…",
            "motivo": ficha.get("motivo_operativo") or ficha.get("motivo") or "…",
            "fecha_prometida": ficha.get("fecha_prometida") or "…",
            "nueva_fecha": ficha.get("nueva_fecha") or "…",
        }

    @classmethod
    def exportar_excel(cls) -> bytes:
        data = cls.cargar()
        filas_guiones = []
        filas_cx = []
        for grupo in data.get("grupos", []):
            for esc in grupo.get("escenarios", []):
                cx = esc.get("cx") or {}
                niveles = esc.get("niveles") or {}
                filas_cx.append(
                    {
                        "Grupo": grupo.get("titulo", ""),
                        "Escenario": esc.get("titulo", ""),
                        "Objetivo": esc.get("objetivo", esc.get("descripcion", "")),
                        "Perfil emocional": ", ".join(esc.get("perfil_emocional", [])),
                        "Empatía": niveles.get("empatia", ""),
                        "Control": niveles.get("control", ""),
                        "Fidelización": niveles.get("fidelizacion", ""),
                        "Descubrimiento": cx.get("descubrimiento", ""),
                        "Solución": cx.get("solucion", ""),
                        "Cierre": cx.get("cierre", ""),
                        "Seguimiento": cx.get("seguimiento", ""),
                        "Consejos asesor": " | ".join(cx.get("consejos_asesor", [])),
                        "Errores comunes": " | ".join(cx.get("errores_comunes", [])),
                    }
                )
                for fase, textos in esc.get("fases", {}).items():
                    filas_guiones.append(
                        {
                            "Grupo": grupo.get("titulo", ""),
                            "Escenario": esc.get("titulo", ""),
                            "Fase": fase.capitalize(),
                            "Canal": "Voz",
                            "Texto": textos.get("voz", ""),
                            "Objetivo": esc.get("objetivo", ""),
                        }
                    )
                    filas_guiones.append(
                        {
                            "Grupo": grupo.get("titulo", ""),
                            "Escenario": esc.get("titulo", ""),
                            "Fase": fase.capitalize(),
                            "Canal": "WhatsApp",
                            "Texto": textos.get("whatsapp", ""),
                            "Objetivo": esc.get("objetivo", ""),
                        }
                    )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(filas_guiones).to_excel(writer, index=False, sheet_name="Guiones")
            pd.DataFrame(filas_cx).to_excel(writer, index=False, sheet_name="Guia CX")
        buffer.seek(0)
        return buffer.getvalue()