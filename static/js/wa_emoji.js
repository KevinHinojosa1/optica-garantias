/**
 * Emojis por code point (ASCII en el archivo = imposible de corromper por encoding).
 * Usar SIEMPRE String.fromCodePoint al armar mensajes de WhatsApp.
 */
(function (global) {
  const CP = {
    calendar: 0x1f4c5, // 📅
    package: 0x1f4e6, // 📦
    store: 0x1f3ea, // 🏪
    page: 0x1f4c4, // 📄
    wave: 0x1f44b, // 👋
    pray: 0x1f64f, // 🙏
    blueHeart: 0x1f499, // 💙
    speech: 0x1f4ac, // 💬
    smile: 0x1f60a, // 😊
    check: 0x2705, // ✅
    pin: 0x1f4cd, // 📍
    person: 0x1f464, // 👤
  };

  function emoji(code) {
    return String.fromCodePoint(code);
  }

  function limpiarTelefonoEC(telefono) {
    let d = String(telefono || '').replace(/\D/g, '');
    if (!d) return '';
    if (d.startsWith('593')) return d;
    if (d.startsWith('0')) d = d.slice(1);
    if (d.length === 9) return `593${d}`;
    return d;
  }

  /**
   * Construye el nombre completo (nombre + apellido si existen).
   * Acepta: nombre_completo, o nombre + apellido/apellidos, o solo nombre.
   */
  function nombreCompleto(it) {
    if (!it) return 'amigo/a';
    // Si ya viene nombre_completo
    if (it.nombre_completo && it.nombre_completo.trim()) return it.nombre_completo.trim();
    const nom = (it.nombre || '').trim();
    const ape = (it.apellido || it.apellidos || '').trim();
    if (nom && ape) return `${nom} ${ape}`;
    if (nom) return nom;
    if (ape) return ape;
    return 'amigo/a';
  }

  /**
   * Mensaje al cliente — script oficial (mismo contenido que el preview).
   */
  function componerMensajeCliente(it, asesor) {
    const producto = (it && it.producto) || 'tu pedido';
    const local = (it && it.local) || 'Óptica Los Andes';
    const factura = (it && (it.factura || it.orden)) || '—';
    const nombre = nombreCompleto(it);
    const as = (asesor || (typeof window !== 'undefined' && window.DEFAULT_ASESOR) || 'Servicio al Cliente').trim();

    const cal = emoji(CP.calendar);
    const pack = emoji(CP.package);
    const store = emoji(CP.store);
    const page = emoji(CP.page);
    const wave = emoji(CP.wave);
    const pray = emoji(CP.pray);
    const heart = emoji(CP.blueHeart);
    const speech = emoji(CP.speech);
    const smile = emoji(CP.smile);

    return [
      `REPROGRAMACIÓN DE ENTREGA`,
      `Producto: ${producto}`,
      `Tienda: ${local}`,
      `Factura: ${factura}`,
      '--------------------',
      `Hola, ${nombre}`,
      '',
      `Te saluda ${as}, de Servicio al Cliente de Óptica Los Andes.`,
      `Queremos contarte que tu orden no estará lista dentro del plazo que te indicamos inicialmente. Lamentamos mucho este cambio y las molestias que pueda ocasionarte.`,
      'Te enviaremos otro mensaje apenas tu pedido esté disponible.',
      `Gracias por tu comprensión.`,
      '--------------------',
      `Si tienes alguna duda, escríbenos con confianza o comunícate con nosotros al 1800-678-422 opción 2.`,
    ].join('\n');
  }

  /**
   * Mensaje a tienda — script oficial actualizado.
   */
  function componerMensajeTienda(it, asesor) {
    const producto = (it && it.producto) || 'N/D';
    const local = (it && it.local) || 'Óptica Los Andes';
    const orden = (it && (it.orden || it.factura)) || 'N/D';
    const proceso = (it && it.proceso) || 'N/D';
    const motivo = (it && it.motivo) || 'N/D';
    const fecha = (it && (it.fecha_reprogramada || it.fecha_indicada)) || 'te confirmamos pronto';
    const as = (asesor || (typeof window !== 'undefined' && window.DEFAULT_ASESOR) || 'Servicio al Cliente').trim();

    return [
      `Buenas tardes, Equipo ${local.toUpperCase()}:`,
      '',
      `Les saluda ${as} de Servicio al Cliente.`,
      '',
      'Por favor, estar pendientes de la llegada del siguiente producto:',
      '',
      `OT: ${orden}`,
      `Proceso: ${proceso}`,
      `Producto: ${producto}`,
      `Motivo: ${motivo}`,
      `Fecha indicada: ${fecha}`,
      '',
      'Si el producto ya llegó a la tienda, por favor comunicarse con el cliente para informarle y coordinar la entrega. Asimismo, agradeceré confirmar por este medio la gestión realizada.',
      '',
      'Muchas gracias por su apoyo.',
    ].join('\n');
  }

  async function copiarAlPortapapeles(texto) {
    const t = String(texto || '');
    if (!t) return false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(t);
        return true;
      }
    } catch { /* fallback abajo */ }
    try {
      const ta = document.createElement('textarea');
      ta.value = t;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }

  /**
   * Abre el chat de WhatsApp.
   * modo "seguro" (default): copia el mensaje y abre el chat VACÍO → pegar = emojis 100% correctos.
   * modo "prefill": intenta prellenar ?text= (puede fallar en algunos clientes).
   */
  async function abrirWhatsAppSeguro(telefono, mensaje, opciones) {
    const opts = opciones || {};
    const modo = opts.modo || 'seguro';
    const num = limpiarTelefonoEC(telefono);
    if (!num) return { ok: false, error: 'No hay número de WhatsApp válido' };
    const texto = String(mensaje || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    if (!texto.trim()) return { ok: false, error: 'El mensaje está vacío' };

    const copiado = await copiarAlPortapapeles(texto);

    let url;
    if (modo === 'prefill') {
      // Codificación manual UTF-8 en percent-encoding (misma idea que encodeURIComponent)
      url = `https://wa.me/${num}?text=${encodeURIComponent(texto)}`;
    } else {
      // Sin texto en la URL: los emojis no pasan por el enlace (causa habitual de �)
      url = `https://wa.me/${num}`;
    }

    const a = document.createElement('a');
    a.setAttribute('href', url);
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    return { ok: true, copiado, modo, url };
  }

  /**
   * Resuelve el número de WhatsApp del local a partir del nombre.
   * Busca en window.TIENDAS_WA_MAP (inyectado desde el backend o definido abajo).
   * Devuelve string con número formato 593XXXXXXXXX o '' si no encuentra.
   */
  function resolverWaTienda(localNombre) {
    if (!localNombre) return '';
    const mapa = (typeof window !== 'undefined' && window.TIENDAS_WA_MAP) || {};
    const norm = localNombre.trim().toLowerCase()
      .replace(/[áàä]/g, 'a').replace(/[éèë]/g, 'e')
      .replace(/[íìï]/g, 'i').replace(/[óòö]/g, 'o')
      .replace(/[úùü]/g, 'u').replace(/ñ/g, 'n');
    // Exacto
    if (mapa[norm]) return mapa[norm];
    // Parcial — buscar la clave que más se parezca
    for (const [clave, num] of Object.entries(mapa)) {
      if (norm.includes(clave) || clave.includes(norm)) return num;
    }
    return '';
  }

  global.WaEmoji = {
    CP,
    emoji,
    nombreCompleto,
    limpiarTelefonoEC,
    resolverWaTienda,
    componerMensajeCliente,
    componerMensajeTienda,
    copiarAlPortapapeles,
    abrirWhatsAppSeguro,
  };
})(typeof window !== 'undefined' ? window : globalThis);
