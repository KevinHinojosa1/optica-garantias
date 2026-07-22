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
   * Mensaje al cliente — script oficial (mismo contenido que el preview).
   */
  function componerMensajeCliente(it, asesor) {
    const producto = (it && it.producto) || 'tu pedido';
    const local = (it && it.local) || 'Óptica Los Andes';
    const factura = (it && (it.factura || it.orden)) || '—';
    const nombre = (it && it.nombre) || 'amigo/a';
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
      `${cal} REPROGRAMACIÓN DE ENTREGA`,
      `${pack} Producto: ${producto}`,
      `${store} Tienda: ${local}`,
      `${page} Factura: ${factura}`,
      '--------------------',
      `Hola, ${nombre} ${wave}`,
      '',
      `Te saluda ${as}, de Servicio al Cliente de Óptica Los Andes.`,
      `Queremos contarte que tu orden no estará lista dentro del plazo que te indicamos inicialmente. Lamentamos mucho este cambio y las molestias que pueda ocasionarte. ${pray}`,
      'Te enviaremos otro mensaje apenas tu pedido esté disponible.',
      `Gracias por tu comprensión. ${heart}`,
      '--------------------',
      `Si tienes alguna duda, escríbenos con confianza o comunícate con nosotros al 1800-678-422 opción 2. ${speech}${smile}`,
    ].join('\n');
  }

  /**
   * Mensaje a tienda — script oficial.
   */
  function componerMensajeTienda(it, asesor) {
    const producto = (it && it.producto) || '—';
    const local = (it && it.local) || 'Óptica Los Andes';
    const factura = (it && (it.factura || it.orden)) || '—';
    const nombre = (it && it.nombre) || '—';
    const as = (asesor || (typeof window !== 'undefined' && window.DEFAULT_ASESOR) || 'Servicio al Cliente').trim();

    const check = emoji(CP.check);
    const wave = emoji(CP.wave);
    const pin = emoji(CP.pin);
    const page = emoji(CP.page);
    const pack = emoji(CP.package);
    const person = emoji(CP.person);
    const pray = emoji(CP.pray);
    const heart = emoji(CP.blueHeart);

    return [
      `${check} MENSAJE ENVIADO AL CLIENTE`,
      '',
      `Hola, equipo ${local} ${wave}`,
      `Les saluda ${as}, de Servicio al Cliente.`,
      'Les confirmo que el mensaje de reprogramación de entrega ya fue enviado al cliente.',
      '',
      `${pin} Tienda: ${local}`,
      `${page} Factura: ${factura}`,
      `${pack} Producto: ${producto}`,
      `${person} Cliente: ${nombre}`,
      '',
      `Por favor, mantenerse pendientes del estado de la orden y, en caso de que el cliente se comunique o se acerque a la tienda, atenderlo con mucha delicadeza, empatía y predisposición, brindándole toda la información disponible. ${pray}${heart}`,
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

  global.WaEmoji = {
    CP,
    emoji,
    limpiarTelefonoEC,
    componerMensajeCliente,
    componerMensajeTienda,
    copiarAlPortapapeles,
    abrirWhatsAppSeguro,
  };
})(typeof window !== 'undefined' ? window : globalThis);
