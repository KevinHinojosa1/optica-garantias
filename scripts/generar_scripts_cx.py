#!/usr/bin/env python3
"""Genera scripts_atencion.json con marco CX corporativo Óptica Los Andes."""
from __future__ import annotations

import json
from pathlib import Path

RUTA_SALIDA = Path(__file__).resolve().parent.parent / "data" / "scripts_atencion.json"

ESCUCHA_ACTIVA = [
    "Lo entiendo perfectamente.",
    "Comprendo cómo se siente.",
    "Gracias por comentármelo.",
    "Aprecio mucho que nos lo informe.",
    "Permítame revisar su caso con detenimiento.",
    "Estoy aquí para ayudarle.",
    "Vamos a solucionarlo juntos.",
    "Entiendo la importancia que esto tiene para usted.",
    "Gracias por su paciencia.",
    "Valoro el tiempo que se ha tomado para comunicarse.",
]

PALABRAS_TRANQUILIDAD = [
    "Permítame ayudarle.",
    "Vamos a revisarlo.",
    "Estoy con usted durante todo el proceso.",
    "Encontraremos la mejor solución.",
    "No se preocupe.",
    "Gracias por su paciencia.",
    "Comprendo completamente.",
    "Revisaremos cada detalle.",
    "Haremos el seguimiento correspondiente.",
    "Puede contar con nosotros.",
    "Su caso es importante para nosotros.",
]

EVITAR = [
    {"frase": "No sé.", "alternativa": "Permítame verificar esa información y en breve le confirmo."},
    {"frase": "Eso no me corresponde.", "alternativa": "Con gusto lo canalizo con el área indicada para que le den una respuesta clara."},
    {"frase": "Tiene que esperar.", "alternativa": "Le indicaré un tiempo estimado real y le mantendré informado/a."},
    {"frase": "Ese no es mi problema.", "alternativa": "Entiendo su situación; voy a acompañarle hasta encontrar la solución."},
    {"frase": "Ya le dijeron.", "alternativa": "Comprendo que esto le genera molestia; revisemos juntos para que quede resuelto."},
    {"frase": "No podemos.", "alternativa": "Déjeme revisar qué alternativas tenemos disponibles para usted."},
    {"frase": "Está equivocado/a.", "alternativa": "Entiendo su punto de vista; permítame explicarle lo que encontramos."},
    {"frase": "Cálmese.", "alternativa": "Comprendo su molestia y lamento la situación; estoy aquí para ayudarle."},
    {"frase": "Eso es imposible.", "alternativa": "Veamos qué opciones sí podemos ofrecerle hoy."},
    {"frase": "No hay nada que hacer.", "alternativa": "Aún tenemos alternativas; permítame orientarle paso a paso."},
]

TECNICAS_TENSION = [
    "Validar emociones antes de explicar.",
    "No contradecir ni discutir.",
    "No justificar antes de escuchar.",
    "Parafrasear el problema del cliente.",
    "Pausas estratégicas y tono pausado.",
    "Hablar con seguridad y calidez.",
]

TECNICAS_PSICO = [
    "Escucha activa",
    "Comunicación No Violenta",
    "Rapport",
    "Validación emocional",
    "PNL — anclaje de calma",
    "Desescalamiento de conflictos",
]

FIDELIZACION = [
    "Gracias por confiar en Óptica Los Andes.",
    "Usted es muy importante para nosotros.",
    "Valoramos su preferencia y su tiempo.",
    "Queremos que se sienta acompañado/a en todo momento.",
    "Estamos comprometidos con su satisfacción.",
]

CIERRE_PERFECTO = (
    "Ha sido un gusto poder ayudarle. Si en cualquier momento necesita asistencia adicional, "
    "estaremos encantados de atenderle. Gracias por confiar en Óptica Los Andes. "
    "Le deseamos un excelente día."
)

SALUDO_ESTANDAR = (
    "Buenos días/tardes, muchas gracias por comunicarse con Óptica Los Andes. "
    "Mi nombre es {asesor}. Será un gusto ayudarle. Cuénteme, ¿en qué puedo asistirle hoy?"
)


def fases(saludo_voz: str, inter_voz: str, cierre_voz: str, saludo_wa: str, inter_wa: str, cierre_wa: str) -> dict:
    return {
        "saludo": {"voz": saludo_voz, "whatsapp": saludo_wa},
        "intermedio": {"voz": inter_voz, "whatsapp": inter_wa},
        "cierre": {"voz": cierre_voz, "whatsapp": cierre_wa},
    }


def wa(s: str) -> str:
    return s.replace("{asesor}", "*{asesor}*").replace("{cliente}", "*{cliente}*").replace("{tienda}", "*{tienda}*")


def guion_base(contexto: str) -> list[dict]:
    return [
        {"actor": "asesor", "texto": SALUDO_ESTANDAR},
        {"actor": "cliente", "texto": f"[Cliente expresa: {contexto}]"},
        {"actor": "asesor", "texto": "Comprendo perfectamente cómo se siente. Gracias por contármelo con tanta claridad."},
        {"actor": "asesor", "texto": "Permítame revisar su caso con detenimiento para ofrecerle la mejor alternativa."},
        {"actor": "cliente", "texto": "[Cliente responde según su emoción: acepta, duda o insiste]"},
        {"actor": "asesor", "texto": "Entiendo la importancia que esto tiene para usted. Vamos a solucionarlo juntos."},
        {"actor": "asesor", "texto": CIERRE_PERFECTO},
    ]


def objeciones_comunes() -> list[dict]:
    return [
        {"situacion": "Cliente se enoja", "respuesta": "Comprendo su molestia y tiene razón en sentirse así. Estoy aquí para escucharle y buscar una solución concreta."},
        {"situacion": "Cliente interrumpe", "respuesta": "Tiene toda mi atención. Permítame anotar cada punto para no omitir nada importante."},
        {"situacion": "Amenaza con no volver", "respuesta": "Valoramos mucho su confianza. Queremos recuperarla con hechos y un seguimiento real."},
        {"situacion": "Pide hablar con supervisor", "respuesta": "Con gusto gestiono la comunicación con la persona indicada y le mantengo informado/a."},
        {"situacion": "Dice que ya llamó varias veces", "respuesta": "Lamento sinceramente que haya tenido que repetir su gestión. Hoy dejaré su caso documentado y con seguimiento."},
        {"situacion": "Compara con otra óptica", "respuesta": "Entiendo la comparación. Permítame mostrarle cómo podemos acompañarle de forma personalizada."},
        {"situacion": "Exige devolución inmediata", "respuesta": "Revisaré de inmediato las opciones disponibles según su compra y le daré una respuesta clara hoy."},
        {"situacion": "No confía en la respuesta", "respuesta": "Comprendo su desconfianza. Le explicaré cada paso con transparencia y por escrito si lo prefiere."},
    ]


def variantes(saludo: str, solucion: str) -> dict:
    return {
        "formal": f"{saludo} Permítame asistirle de inmediato. {solucion}",
        "calida": f"{saludo} Con mucho gusto le acompaño. {solucion}",
        "empatica": f"{saludo} Comprendo cómo se siente y estoy aquí para ayudarle. {solucion}",
        "breve": f"{saludo} {solucion} ¿Le parece bien?",
        "premium": f"{saludo} Su caso es prioritario para nosotros. {solucion} Quedo personalmente pendiente de usted.",
    }


def escenario(
    id_: str,
    titulo: str,
    objetivo: str,
    perfil: list[str],
    fases_dict: dict,
    *,
    empatia: int = 8,
    control: int = 8,
    fidelizacion_n: int = 7,
    descubrimiento: str = "",
    investigacion: str = "",
    solucion: str = "",
    seguimiento: str = "",
    consejos: list[str] | None = None,
    errores: list[str] | None = None,
    palabras_clave: list[str] | None = None,
    guion: list[dict] | None = None,
    objeciones: list[dict] | None = None,
    variantes_dict: dict | None = None,
    requiere_fechas: bool = False,
) -> dict:
    saludo_v = fases_dict["saludo"]["voz"]
    sol = solucion or "Le confirmaré los pasos concretos y el tiempo estimado."
    return {
        "id": id_,
        "titulo": titulo,
        "objetivo": objetivo,
        "descripcion": objetivo,
        "perfil_emocional": perfil,
        "niveles": {"empatia": empatia, "control": control, "fidelizacion": fidelizacion_n},
        "requiere_fechas": requiere_fechas,
        "fases": fases_dict,
        "cx": {
            "descubrimiento": descubrimiento or "¿Podría contarme un poco más para orientarle mejor?",
            "escucha_activa": ESCUCHA_ACTIVA,
            "validacion_emocional": [
                "Comprendo cómo se siente.",
                "Su reacción es completamente válida.",
                "Gracias por expresarlo con tanta claridad.",
            ],
            "investigacion": investigacion or "Permítame revisar su expediente y confirmar los detalles.",
            "solucion": sol,
            "tecnicas_tension": TECNICAS_TENSION,
            "palabras_tranquilidad": PALABRAS_TRANQUILIDAD,
            "evitar": EVITAR,
            "guion": guion or guion_base(titulo.lower()),
            "objeciones": objeciones or objeciones_comunes(),
            "variantes": variantes_dict or variantes(saludo_v[:80], sol),
            "fidelizacion": FIDELIZACION,
            "cierre": CIERRE_PERFECTO,
            "seguimiento": seguimiento or "Contactar al cliente en 24-48 h para confirmar satisfacción.",
            "consejos_asesor": consejos or [
                "Mantenga tono cálido y pausado.",
                "No interrumpa; valide antes de proponer.",
                "Confirme acuerdos antes de cerrar.",
            ],
            "errores_comunes": errores or [
                "Justificar antes de escuchar.",
                "Usar lenguaje frío o técnico.",
                "Cerrar sin confirmar que el cliente quedó conforme.",
            ],
            "tecnicas_psicologicas": TECNICAS_PSICO,
            "palabras_clave": palabras_clave or ["confianza", "acompañamiento", "solución", "empatía"],
        },
    }


def grupo_servicio_cliente() -> dict:
    escenarios = []
    items = [
        ("info_general", "Cliente solicita información", ["Curioso", "Cliente nuevo"], "Brindar información clara y generar confianza desde el primer contacto.", "¿Sobre qué tema le gustaría que le oriente: productos, precios, garantías o promociones?"),
        ("promociones", "Cliente consulta promociones", ["Interesado", "Comparando opciones"], "Informar promociones vigentes sin presión y guiar hacia la mejor opción.", "¿Busca promoción en monturas, lunas o lentes de contacto?"),
        ("horarios", "Cliente pregunta horarios", ["Práctico", "Apurado"], "Facilitar horarios de atención y ofrecer alternativa de cita.", "¿De qué tienda necesita el horario?"),
        ("ubicacion", "Cliente pregunta ubicación", ["Confundido", "Cliente nuevo"], "Orientar ubicación con claridad y cercanía.", "¿Desde qué zona nos contacta para indicarle la tienda más cercana?"),
        ("productos", "Cliente consulta productos", ["Explorando", "Indeciso"], "Asesorar sobre productos según necesidad visual y estilo de vida.", "¿Busca gafas graduadas, de sol o lentes de contacto?"),
        ("asesoria_lentes", "Asesoría para elegir lentes", ["Indeciso", "Ansioso"], "Guiar con consultoría personalizada sin presión de compra.", "¿Para qué actividades usará sus lentes principalmente?"),
        ("cita", "Cliente necesita una cita", ["Organizado", "Cliente nuevo"], "Agendar cita de forma ágil y confirmar detalles.", "¿Prefiere examen visual, entrega o ajuste de montura?"),
        ("reprogramar_cita", "Reprogramar una cita", ["Apurado", "Molesto leve"], "Reprogramar con empatía y ofrecer alternativas.", "¿Qué fecha y horario le resultaría más conveniente?"),
    ]
    for id_, titulo, perfil, objetivo, descubrimiento in items:
        sv = (
            "Buenos días/tardes, muchas gracias por comunicarse con Óptica Los Andes. "
            "Mi nombre es {asesor}, de {tienda}. Será un gusto ayudarle. "
            f"Cuénteme, ¿en qué puedo asistirle con {titulo.lower()}?"
        )
        escenarios.append(
            escenario(
                id_,
                titulo,
                objetivo,
                perfil,
                fases(
                    sv,
                    f"Gracias, {{cliente}}. {descubrimiento} Permítame orientarle con información clara y precisa.",
                    f"Perfecto, {{cliente}}. {CIERRE_PERFECTO}",
                    wa(f"Buenos días/tardes, *{{cliente}}*. 👋\n\nLe saluda *{{asesor}}* de *{{tienda}}*, Óptica Los Andes.\n\nSerá un gusto ayudarle.\n\n{descubrimiento}"),
                    wa("Gracias por su mensaje. Le comparto la información solicitada con gusto. ¿Desea que le reserve una cita?"),
                    wa(f"Ha sido un gusto atenderle. *Gracias por confiar en Óptica Los Andes* 💙"),
                ),
                descubrimiento=descubrimiento,
                empatia=7,
                control=8,
                fidelizacion_n=8,
            )
        )
    return {"id": "servicio_cliente", "titulo": "Servicio al Cliente", "categoria_cx": "Servicio al Cliente", "escenarios": escenarios}


def grupo_posventa_cx() -> dict:
    specs = [
        ("sin_recibir_lentes", "Cliente aún no recibe sus lentes", ["Ansioso", "Decepcionado"], "Tranquilizar, informar estado real y comprometer seguimiento.", "¿Cuándo le indicaron que estarían listos?"),
        ("retraso_entrega", "Retraso en la entrega", ["Molesto", "Impaciente"], "Admitir retraso, explicar causa y dar fecha firme.", "¿Recuerda la fecha que le prometieron?"),
        ("producto_defectuoso", "Producto defectuoso", ["Molesto", "Decepcionado"], "Validar molestia y activar garantía o cambio.", "¿Podría describirme el defecto que observa?"),
        ("adaptacion_lentes", "Adaptación a lentes nuevos", ["Confundido", "Ansioso"], "Orientar periodo de adaptación y ofrecer revisión.", "¿Desde cuándo usa los lentes y qué síntoma nota?"),
        ("garantia", "Consulta de garantía", ["Desconfiado", "Preocupado"], "Explicar cobertura y pasos con transparencia.", "¿Qué inconveniente presenta con su producto?"),
        ("cambio_montura", "Cambio de montura", ["Indeciso", "Exigente"], "Asesorar cambio según política y preferencias.", "¿Busca cambio por estilo, talla o garantía?"),
        ("cambio_lunas", "Cambio de lunas", ["Exigente", "Decepcionado"], "Evaluar opción de cambio y tiempos.", "¿Qué aspecto de las lunas no cumple su expectativa?"),
        ("reparacion", "Reparación", ["Práctico", "Apurado"], "Coordinar reparación con tiempo y costo claros.", "¿Qué pieza necesita reparación?"),
        ("ajuste_montura", "Ajuste de montura", ["Práctico"], "Agendar ajuste y explicar que es sin costo en tienda.", "¿Le molesta en nariz, orejas o se le resbala?"),
        ("inconforme_resultado", "Inconforme con el resultado", ["Decepcionado", "Molesto"], "Escuchar, validar y proponer revisión optométrica.", "¿Qué aspecto del resultado no le convence?"),
        ("no_ve_bien", "Cliente indica que no ve bien", ["Ansioso", "Preocupado"], "Priorizar revisión y tranquilizar sobre adaptación o receta.", "¿La dificultad es de lejos, de cerca o en ambos?"),
        ("devolucion", "Cliente quiere devolución", ["Molesto", "Exigente"], "Escuchar motivo y aplicar política con empatía.", "¿Podría contarme qué le llevó a solicitar la devolución?"),
        ("reclamo_demora", "Reclamo por demora", ["Molesto", "Impaciente"], "Reconocer demora y dar plan con fecha.", "¿Cuánto tiempo lleva esperando?"),
        ("perdio_factura", "Cliente perdió la factura", ["Preocupado", "Confundido"], "Buscar compra en sistema y orientar sin culpar.", "¿Recuerda fecha aproximada y tienda de compra?"),
        ("estado_pedido", "Estado del pedido", ["Ansioso", "Apurado"], "Informar estado actual y próximo paso.", "¿Tiene a mano su número de factura o cédula?"),
    ]
    escenarios = []
    for id_, titulo, perfil, objetivo, descubrimiento in specs:
        escenarios.append(
            escenario(
                id_,
                titulo,
                objetivo,
                perfil,
                fases(
                    f"Buenos días/tardes, {{cliente}}. Le habla {{asesor}} de Óptica Los Andes, {{tienda}}. Gracias por comunicarse. Entiendo su situación y estoy aquí para ayudarle.",
                    f"Gracias por contarme, {{cliente}}. {descubrimiento} Permítame revisar su caso y le confirmo los pasos a seguir.",
                    f"{{cliente}}, quedamos en seguimiento. {CIERRE_PERFECTO}",
                    wa(f"Buenos días/tardes, *{{cliente}}*. Le saluda *{{asesor}}* de *{{tienda}}*.\n\nComprendo su situación y estoy aquí para ayudarle 🤝"),
                    wa(f"Gracias por su mensaje. {descubrimiento}\n\nRevisaré su caso y le confirmo los pasos ✅"),
                    wa("Gracias por su paciencia. Seguimos pendientes de usted 💙"),
                ),
                descubrimiento=descubrimiento,
                empatia=9,
                control=8,
                fidelizacion_n=8,
            )
        )
    return {"id": "posventa_cx", "titulo": "Posventa", "categoria_cx": "Posventa", "escenarios": escenarios}


def grupo_fidelizacion() -> dict:
    specs = [
        ("seguimiento", "Llamada de seguimiento", ["Neutral", "Cliente frecuente"], "Confirmar satisfacción post-compra."),
        ("satisfaccion", "Confirmar satisfacción", ["Feliz", "Neutral"], "Medir satisfacción y detectar oportunidades."),
        ("mantenimiento", "Recordar mantenimiento", ["Olvidadizo", "Práctico"], "Recordar limpieza y revisión de montura."),
        ("examen_visual", "Invitar a nuevo examen visual", ["Saludable", "Cliente frecuente"], "Promover salud visual preventiva."),
        ("promo_exclusiva", "Promociones exclusivas", ["Interesado", "Cliente frecuente"], "Ofrecer beneficio sin presión."),
        ("inactivos", "Recuperar clientes inactivos", ["Distante", "Desconfiado"], "Reconectar con valor genuino."),
        ("cumpleanos", "Felicitar cumpleaños", ["Feliz"], "Generar vínculo emocional positivo."),
        ("agradecer_compra", "Agradecer una compra", ["Feliz", "Cliente nuevo"], "Reforzar confianza post-venta."),
        ("solicitar_resena", "Solicitar reseña", ["Satisfecho"], "Pedir reseña de forma amable."),
        ("recomendacion", "Solicitar recomendación", ["Feliz", "Cliente frecuente"], "Invitar a recomendar sin presión."),
        ("referidos", "Programa de referidos", ["Interesado"], "Explicar programa de referidos con claridad."),
    ]
    escenarios = []
    for id_, titulo, perfil, objetivo in specs:
        escenarios.append(
            escenario(
                id_,
                titulo,
                objetivo,
                perfil,
                fases(
                    f"Buenos días/tardes, {{cliente}}. Le habla {{asesor}} de Óptica Los Andes. Me comunico con usted para {titulo.lower()}. ¿Tiene un momento?",
                    "Gracias por su tiempo. Lo que me comenta es muy valioso para nosotros.",
                    f"{{cliente}}, ha sido un gusto saludarle. {CIERRE_PERFECTO}",
                    wa(f"Buenos días/tardes, *{{cliente}}*. Le saluda *{{asesor}}* de Óptica Los Andes.\n\nMe comunico para {titulo.lower()} 🤝"),
                    wa("Gracias por su tiempo. Valoramos mucho su respuesta 💙"),
                    wa("*Gracias por confiar en Óptica Los Andes* 🌟"),
                ),
                empatia=8,
                control=7,
                fidelizacion_n=9,
            )
        )
    return {"id": "fidelizacion", "titulo": "Fidelización", "categoria_cx": "Fidelización", "escenarios": escenarios}


def grupo_clientes_dificiles() -> dict:
    specs = [
        ("cliente_molesto", "Cliente muy molesto", ["Molesto"], 9, 9, 8),
        ("cliente_agresivo", "Cliente agresivo", ["Molesto", "Agresivo"], 10, 9, 7),
        ("cliente_griton", "Cliente que grita", ["Molesto", "Alterado"], 10, 10, 7),
        ("cliente_impaciente", "Cliente impaciente", ["Impaciente", "Apurado"], 7, 9, 7),
        ("cliente_desconfiado", "Cliente desconfiado", ["Desconfiado"], 9, 8, 8),
        ("cliente_exigente", "Cliente exigente", ["Exigente"], 8, 9, 7),
        ("amenaza_denuncia", "Amenaza con denunciar", ["Molesto", "Amenazante"], 10, 9, 6),
        ("comentarios_negativos", "Comentarios negativos en redes", ["Molesto", "Público"], 9, 8, 7),
        ("pide_gerente", "Exige hablar con el gerente", ["Exigente", "Molesto"], 8, 9, 7),
        ("no_acepta_solucion", "No acepta la solución", ["Molesto", "Frustrado"], 9, 9, 6),
    ]
    escenarios = []
    for id_, titulo, perfil, emp, ctrl, fid in specs:
        escenarios.append(
            escenario(
                id_,
                titulo,
                f"Manejar {titulo.lower()} con empatía, control emocional y solución concreta.",
                perfil,
                fases(
                    f"Buenos días/tardes, {{cliente}}. Le habla {{asesor}} de Óptica Los Andes, {{tienda}}. Comprendo que usted está molesto/a y tiene razón en sentirse así. Estoy aquí para escucharle y ayudarle.",
                    "Gracias por contarme. Lo que usted indica es válido. Permítame revisar su caso y en breve le daré una respuesta clara.",
                    f"{{cliente}}, gracias por su paciencia. {CIERRE_PERFECTO}",
                    wa(f"Buenos días/tardes, *{{cliente}}*. Le saluda *{{asesor}}* de *{{tienda}}*.\n\n*Comprendo su molestia* y estoy aquí para escucharle 🤝"),
                    wa("Gracias por su mensaje. Lo que indica es *totalmente válido*. Revisaré su caso y le confirmo los pasos ✅"),
                    wa("*Gracias por darnos la oportunidad de ayudarle* 💙"),
                ),
                empatia=emp,
                control=ctrl,
                fidelizacion_n=fid,
                consejos=[
                    "Hable más bajo si el cliente grita.",
                    "No tome los comentarios de forma personal.",
                    "Documente acuerdos por escrito.",
                ],
            )
        )
    return {"id": "clientes_dificiles", "titulo": "Clientes difíciles", "categoria_cx": "Clientes difíciles", "escenarios": escenarios}


def grupo_ventas_consultivas() -> dict:
    productos = [
        ("antirreflejo", "Antirreflejo", "Reducir reflejos y mejorar confort visual sin presión."),
        ("filtro_azul", "Filtro azul", "Protección frente a pantallas con enfoque en bienestar."),
        ("fotocromaticos", "Fotocromáticos", "Comodidad interior/exterior en un solo lente."),
        ("polarizados", "Polarizados", "Mayor confort al aire libre y manejo."),
        ("multifocales", "Multifocales", "Solución integral para visión lejos y cerca."),
        ("segunda_compra", "Segunda compra", "Segundo par con beneficio consultivo."),
        ("accesorios", "Accesorios", "Complementos útiles para cuidado diario."),
        ("estuche_premium", "Estuche premium", "Protección y durabilidad con valor agregado."),
        ("liquidos_limpieza", "Líquidos de limpieza", "Mantenimiento correcto de lentes."),
        ("garantia_extendida", "Garantías extendidas", "Tranquilidad adicional explicada con claridad."),
    ]
    escenarios = []
    for id_, titulo, objetivo in productos:
        escenarios.append(
            escenario(
                id_,
                f"Ofrecer {titulo.lower()}",
                objetivo,
                ["Indeciso", "Interesado"],
                fases(
                    f"{{cliente}}, según lo que me comenta de su estilo de vida, le podría recomendar {titulo.lower()}. ¿Le gustaría que le explique cómo le beneficiaría?",
                    f"Muchos clientes con un perfil similar han notado mayor comodidad con {titulo.lower()}. Sin compromiso, ¿le gustaría conocer opciones y valores?",
                    "Perfecto. Cuando guste, con gusto profundizamos. Ha sido un gusto orientarle.",
                    wa(f"{{cliente}}, según su necesidad visual, *{titulo.lower()}* podría ayudarle mucho 👓\n\n¿Le gustaría que le explique los beneficios *sin compromiso*?"),
                    wa("Con gusto le comparto opciones adaptadas a su presupuesto y estilo de vida."),
                    wa("Gracias por su interés. Estamos para orientarle cuando lo desee 💙"),
                ),
                empatia=7,
                control=8,
                fidelizacion_n=8,
                consejos=[
                    "Nunca presione; ofrezca valor y deje que el cliente decida.",
                    "Relacione el producto con su necesidad real.",
                    "Use preguntas abiertas antes de recomendar.",
                ],
                palabras_clave=["consultivo", "beneficio", "sin presión", "personalizado"],
            )
        )
    return {"id": "ventas_consultivas", "titulo": "Ventas consultivas", "categoria_cx": "Ventas consultivas", "escenarios": escenarios}


def grupo_situaciones_operativas() -> dict:
    return {
        "id": "situaciones_operativas",
        "titulo": "Situaciones operativas",
        "categoria_cx": "Posventa",
        "escenarios": [
            escenario(
                "reprogramacion",
                "Reprogramación de cita o entrega",
                "Avise con anticipación, explique el motivo con honestidad y ofrezca alternativas.",
                ["Molesto leve", "Apurado"],
                fases(
                    "Buenos días/tardes, {cliente}. Le habla {asesor} de Óptica Los Andes, {tienda}. Le contacto con honestidad: necesitamos reprogramar su cita o entrega del {fecha_prometida}. Lamento el cambio.",
                    "El motivo es: {motivo}. Le puedo ofrecer el {nueva_fecha}, o ajustamos a otro día. ¿Cuál le conviene?",
                    "Perfecto, {cliente}. Queda confirmado para el {nueva_fecha}. Disculpe las molestias y gracias por su comprensión.",
                    wa("Buenos días/tardes, *{cliente}*. Le saluda *{asesor}* de *{tienda}*.\n\nNecesitamos *reprogramar* su cita/entrega del *{fecha_prometida}*. Lamentamos el cambio."),
                    wa("*Motivo:* {motivo}\n*Nueva fecha:* {nueva_fecha}\n¿Le conviene?"),
                    wa("Confirmado para *{nueva_fecha}*. Gracias por su comprensión 💙"),
                ),
                requiere_fechas=True,
            ),
            escenario(
                "retraso_envio",
                "Lentes no enviados en fecha prometida",
                "Admita el retraso, explique la causa y dé una nueva fecha firme.",
                ["Molesto", "Decepcionado"],
                fases(
                    "Buenos días/tardes, {cliente}. Le habla {asesor} de Óptica Los Andes, {tienda}. Sé que esperaba sus lentes para el {fecha_prometida} y aún no los ha recibido. Le pido disculpas sinceras.",
                    "Le explico con honestidad: {motivo}. La nueva fecha estimada es el {nueva_fecha}. Le haré seguimiento personal.",
                    "Gracias, {cliente}, por su paciencia. Confirmamos entrega para el {nueva_fecha}.",
                    wa("Buenos días/tardes, *{cliente}*. Esperaba su *{producto}* para el *{fecha_prometida}* y aún no lo recibe. *Disculpas sinceras*."),
                    wa("*Motivo:* {motivo}\n*Nueva fecha:* {nueva_fecha}\nSeguimiento personal 📲"),
                    wa("Entrega confirmada para *{nueva_fecha}*. Gracias por su paciencia 🙏"),
                ),
                requiere_fechas=True,
            ),
        ],
    }


def grupo_posventa_calificacion() -> dict:
    return {
        "id": "posventa",
        "titulo": "Posventa — calificación baja",
        "categoria_cx": "Posventa",
        "solo_asesor_cliente": True,
        "palabras_calma": [
            {
                "situacion": "Inicio de llamada",
                "frases": [
                    "Me comunico con usted porque hace poco realizó una compra con nosotros y nos importa mucho saber cómo fue su experiencia.",
                    "Le llamo solo un momentito, no le quito mucho tiempo.",
                    "No vengo a justificar nada; solo a conocer cómo fue su experiencia.",
                ],
            },
            {
                "situacion": "Cliente molesto o triste",
                "frases": [
                    "Comprendo perfectamente cómo se siente.",
                    "Tiene toda la razón en sentirse así.",
                    "Lamento que su experiencia no haya sido la que usted esperaba.",
                ],
            },
            {
                "situacion": "Mientras el cliente habla",
                "frases": [
                    "Gracias por contarme, lo valoro mucho.",
                    "Entiendo, gracias por ser tan honesto/a conmigo.",
                    "Tiene sentido lo que me dice.",
                ],
            },
            {
                "situacion": "Cierre amable",
                "frases": [
                    "Muchas gracias por su tiempo y por su sinceridad.",
                    "Su comentario ya quedó registrado para que el equipo lo revise.",
                    "Que tenga un excelente día, {cliente}.",
                ],
            },
        ],
        "escenarios": [
            escenario(
                "llamada_mala_calificacion",
                "Llamada por mala calificación",
                "Llamada breve de experiencia: escuchar sin justificar y cerrar sin indagar de más.",
                ["Decepcionado", "Molesto leve"],
                fases(
                    "Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes. Me comunico con usted porque hace poco realizó una compra con nosotros y nos importa mucho saber cómo fue su experiencia. ¿Cómo le fue en general?",
                    "Gracias por contarme, {cliente}. Comprendo cómo se sintió y lamento que no haya sido la experiencia que esperaba. Con lo que me compartió es suficiente.",
                    "Muchas gracias, {cliente}, por su tiempo y honestidad. Su comentario quedó registrado. Que tenga un excelente día.",
                    wa("Buenos días/tardes, *{cliente}*. Le saluda *{asesor}*.\n\nMe comunico porque *hace poco realizó una compra con nosotros* y nos importa saber *cómo fue su experiencia*."),
                    wa("Gracias por contarnos. Lo que compartió es muy valioso y quedó registrado 💙"),
                    wa("Gracias por su tiempo. Que tenga un excelente día 🌟"),
                ),
                empatia=9,
                control=8,
                fidelizacion_n=8,
            ),
            escenario(
                "seguimiento_posventa",
                "Seguimiento breve",
                "Confirmar que el comentario fue recibido sin abrir nuevas indagaciones.",
                ["Neutral"],
                fases(
                    "Buenos días/tardes, {cliente}. Le habla nuevamente {asesor} de Óptica Los Andes. Le llamo para confirmarle que su comentario ya fue compartido con el equipo.",
                    "Perfecto, {cliente}. Solo quería dejarle esa confirmación. Gracias por su paciencia.",
                    "Gracias nuevamente, {cliente}. Valoramos que nos haya dado la oportunidad de escucharle.",
                    wa("Buenos días/tardes, *{cliente}*. Le saluda *{asesor}*.\n\nConfirmamos que su comentario *ya fue compartido* con el equipo ✅"),
                    wa("Solo queríamos dejarle esa confirmación. Gracias por su paciencia 🤝"),
                    wa("Gracias por confiar en Óptica Los Andes 💙"),
                ),
            ),
        ],
    }


def grupo_garantia_no_aprobada() -> dict:
    return {
        "id": "garantia_no_aprobada",
        "titulo": "Garantía no aprobada — retiro en tienda",
        "categoria_cx": "Posventa",
        "solo_asesor_cliente": True,
        "situaciones_retiro": [
            {
                "situacion": "Informar que no se aprobó la garantía",
                "frases": [
                    "{cliente}, le comento con respeto que la garantía no fue aprobada en esta ocasión.",
                    "Entendemos que esta noticia no es la que usted esperaba.",
                ],
            },
            {
                "situacion": "Invitar a retirar en tienda",
                "frases": [
                    "Puede acercarse a la tienda donde realizó su compra para retirar sus lentes o gafas.",
                    "Puede pasar en el horario que le quede más cómodo con su documento de identidad.",
                ],
            },
            {
                "situacion": "Cliente molesto",
                "frases": [
                    "Comprendo su molestia y escucho lo que me dice.",
                    "En tienda con gusto le explican el detalle de la revisión.",
                ],
            },
        ],
        "escenarios": [
            escenario(
                "retiro_lentes",
                "Retiro de lentes oftálmicos",
                "Informar garantía no aprobada e indicar retiro de lentes en tienda.",
                ["Decepcionado", "Molesto"],
                fases(
                    "Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes. Le informo el resultado de la revisión de garantía de sus lentes.",
                    "{cliente}, con respeto le comento que la garantía no fue aprobada. Sus lentes pueden retirarse en la tienda donde compró.",
                    "Gracias, {cliente}. En tienda con gusto le orientan. Que tenga un buen día.",
                    wa("Buenos días/tardes, *{cliente}*. Le saluda *{asesor}*.\n\nLe informamos el resultado de la *revisión de garantía* de sus lentes."),
                    wa("La *garantía no fue aprobada*. Sus *lentes* pueden *retirarse en la tienda* donde compró."),
                    wa("Gracias por su tiempo 💙"),
                ),
            ),
            escenario(
                "retiro_gafas",
                "Retiro de gafas",
                "Informar garantía no aprobada e indicar retiro de gafas.",
                ["Decepcionado"],
                fases(
                    "Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes. Le llamo por el resultado de la garantía de sus gafas.",
                    "Lamentamos informarle que la garantía no fue aprobada. Sus gafas están disponibles para retiro en tienda.",
                    "Gracias, {cliente}. Puede acercarse con su documento. Que esté muy bien.",
                    wa("Buenos días, *{cliente}*. Resultado de *garantía* de sus gafas."),
                    wa("*Garantía no aprobada*. *Gafas* disponibles para *retiro en tienda*."),
                    wa("Gracias por su comprensión 🙏"),
                ),
            ),
            escenario(
                "retiro_contacto",
                "Retiro de lentes de contacto",
                "Informar garantía no aprobada e indicar retiro.",
                ["Decepcionado"],
                fases(
                    "Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes. Por el resultado de garantía de sus lentes de contacto.",
                    "La garantía no fue aprobada. Puede retirarlos en la tienda donde compró.",
                    "Gracias, {cliente}. En tienda le entregarán su pedido.",
                    wa("Buenos días, *{cliente}*. Resultado de garantía — *lentes de contacto*."),
                    wa("*Garantía no aprobada*. Retiro en *tienda*."),
                    wa("Gracias por su comprensión 💙"),
                ),
            ),
            escenario(
                "retiro_general",
                "Retiro de pedido (general)",
                "Garantía no aprobada; retiro de lo comprado en tienda.",
                ["Decepcionado", "Confundido"],
                fases(
                    "Buenos días/tardes, ¿hablo con {cliente}? Le habla {asesor} de Óptica Los Andes. Por el resultado de la garantía de su compra.",
                    "La garantía no fue aprobada. Lo que compró — lentes, gafas o su producto — puede retirarse en la tienda donde compró.",
                    "Gracias, {cliente}. En tienda con gusto le ayudan.",
                    wa("Buenos días, *{cliente}*. Resultado de *garantía* de su compra."),
                    wa("*Garantía no aprobada*. Puede *retirar en tienda* lo que compró."),
                    wa("Gracias por su tiempo 🙏"),
                ),
            ),
        ],
    }


def generar() -> dict:
    return {
        "version": "2.0",
        "marco": "CX Corporativo Óptica Los Andes",
        "grupos": [
            grupo_servicio_cliente(),
            grupo_posventa_cx(),
            grupo_fidelizacion(),
            grupo_clientes_dificiles(),
            grupo_ventas_consultivas(),
            grupo_situaciones_operativas(),
            grupo_posventa_calificacion(),
            grupo_garantia_no_aprobada(),
        ],
    }


def main() -> None:
    data = generar()
    RUTA_SALIDA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(g["escenarios"]) for g in data["grupos"])
    print(f"✅ Generados {len(data['grupos'])} grupos, {total} escenarios → {RUTA_SALIDA}")


if __name__ == "__main__":
    main()