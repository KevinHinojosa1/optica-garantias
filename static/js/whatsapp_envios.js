/**
 * Reprogramación de entregas — cliente / tienda / correo + contador diario
 */

let contactos = [];
let itemsEnvio = [];
let correosPorLocal = [];
let itemSeleccionado = null;
let colaEnvio = [];
let indiceCola = 0;
let autoTimer = null;
let businessApiActiva = false;
let smtpActivo = false;
let enviandoBusiness = false;

function toast(msg, tipo = 'info') {
  const el = document.getElementById('toast-wa');
  if (!el) return;
  el.textContent = msg;
  el.className = `fixed bottom-4 right-4 z-50 glass-card px-4 py-3 text-sm font-medium shadow-lg toast-${tipo}`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 4000);
}

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function asesorActual() {
  return document.getElementById('wa-asesor')?.value.trim() || window.DEFAULT_ASESOR || 'Servicio al Cliente';
}

function modoPrefillActivo() {
  return !!document.getElementById('wa-prefill-url')?.checked;
}

/** Recompone mensajes con emojis por code point (nunca confiar en encoding del servidor para WA). */
function refrescarMensajesItem(it) {
  if (!it || !window.WaEmoji) return it;
  const as = asesorActual();
  it.mensaje_cliente = WaEmoji.componerMensajeCliente(it, as);
  it.mensaje_tienda = WaEmoji.componerMensajeTienda(it, as);
  it.mensaje = it.mensaje_cliente;
  return it;
}

function buildWaLink(telefono, mensaje) {
  const num = (window.WaEmoji && WaEmoji.limpiarTelefonoEC(telefono)) || String(telefono || '').replace(/\D/g, '');
  if (!num) return '';
  return `https://wa.me/${num}?text=${encodeURIComponent(String(mensaje || ''))}`;
}

/**
 * Abre WhatsApp en modo SEGURO (default):
 * 1) Arma el mensaje con emojis correctos (fromCodePoint)
 * 2) Copia al portapapeles
 * 3) Abre el chat SIN ?text=  → el usuario pega y los emojis salen bien en Web/Android/iOS
 *
 * Si marca "prellenar en el enlace", intenta ?text= (puede fallar en algunos clientes).
 */
async function abrirWhatsApp(telefono, mensaje) {
  if (!window.WaEmoji) {
    toast('Error: no se cargó el módulo de emojis. Recargue la página (Cmd+Shift+R).', 'error');
    return false;
  }
  const modo = modoPrefillActivo() ? 'prefill' : 'seguro';
  const result = await WaEmoji.abrirWhatsAppSeguro(telefono, mensaje, { modo });
  if (!result.ok) {
    toast(result.error || 'No se pudo abrir WhatsApp', 'error');
    return false;
  }
  if (modo === 'seguro') {
    toast(
      result.copiado
        ? '📋 Mensaje copiado. En WhatsApp: pega con Ctrl+V (o mantener → Pegar). Los emojis saldrán bien.'
        : 'WhatsApp abierto. Copia el mensaje del recuadro y pégalo en el chat.',
      'ok',
    );
  } else {
    toast(
      result.copiado
        ? 'WhatsApp abierto (texto en enlace). Si ves rombos, desmarca prellenar y vuelve a intentar.'
        : 'WhatsApp abierto.',
      'ok',
    );
  }
  return true;
}

function openWhatsApp(telefono, mensaje) {
  return abrirWhatsApp(telefono, mensaje);
}

/** WA cliente: recompone mensaje oficial + envío seguro */
async function abrirWaClienteDesdePreview() {
  const it = itemSeleccionado;
  if (!it) {
    toast('Seleccione un contacto de la tabla', 'info');
    return;
  }
  refrescarMensajesItem(it);
  const mensaje = it.mensaje_cliente;
  document.getElementById('preview-cliente').value = mensaje;
  const tel = it.telefono_limpio || it.telefono || '';
  await abrirWhatsApp(tel, mensaje);
}

/** WA tienda: recompone + envío seguro al grupo */
async function abrirWaTiendaDesdePreview() {
  const it = itemSeleccionado;
  if (!it) {
    toast('Seleccione un contacto de la tabla', 'info');
    return;
  }
  refrescarMensajesItem(it);
  const mensaje = it.mensaje_tienda;
  document.getElementById('preview-tienda').value = mensaje;

  let tel = '';
  const waTi = it.wa_link_tienda || '';
  if (waTi) {
    try {
      const u = new URL(waTi, 'https://wa.me');
      tel = u.searchParams.get('phone') || '';
      if (!tel) {
        const m = String(u.pathname || waTi).match(/(\d{10,15})/);
        if (m) tel = m[1];
      }
    } catch {
      const m = String(waTi).match(/(\d{10,15})/);
      if (m) tel = m[1];
    }
  }
  if (!tel) {
    toast('No hay WhatsApp de tienda para este local', 'error');
    return;
  }
  await abrirWhatsApp(tel, mensaje);
}

function modoEnvio() {
  return document.getElementById('wa-modo-business')?.checked ? 'business' : 'wame';
}

function payloadBase(registrarLog = true) {
  return {
    plantilla: window.WA_PLANTILLA_EJEMPLO || 'ok',
    asesor: document.getElementById('wa-asesor').value.trim() || window.DEFAULT_ASESOR || '',
    incluir_pie: true,
    fecha_reprogramada: document.getElementById('wa-fecha-reprog')?.value.trim() || '',
    fecha_anterior: document.getElementById('wa-fecha-anterior')?.value.trim() || '',
    hora: document.getElementById('wa-hora')?.value.trim() || '',
    motivo: document.getElementById('wa-motivo')?.value.trim() || '',
    registrar_log: registrarLog,
    contactos,
  };
}

function actualizarBotones() {
  const hayContactos = contactos.length > 0;
  const hayItems = itemsEnvio.length > 0;
  document.getElementById('btn-generar').disabled = !hayContactos;
  document.getElementById('btn-exportar').disabled = !hayContactos;
  document.getElementById('btn-enviar-masivo').disabled = !hayItems;
}

function actualizarKpis() {
  const total = itemsEnvio.length || contactos.length;
  const validos = itemsEnvio.filter(i => i.valido).length;
  const enviados = itemsEnvio.filter(i => i._enviado).length;
  const pendientes = validos - enviados;
  document.getElementById('kpi-total').textContent = total;
  document.getElementById('kpi-validos').textContent = itemsEnvio.length ? validos : contactos.length;
  document.getElementById('kpi-enviados').textContent = enviados;
  document.getElementById('kpi-pendientes').textContent = itemsEnvio.length ? Math.max(0, pendientes) : contactos.length;
}

function pintarResumenDia(resumen) {
  if (!resumen) return;
  document.getElementById('kpi-hoy').textContent = resumen.total_cliente || 0;
  const box = document.getElementById('resumen-hoy');
  if (!box) return;
  const locales = resumen.por_local || [];
  const fuente = resumen.fuente === 'base_de_datos' ? ' · 💾 BD' : '';
  if (!locales.length) {
    box.innerHTML = `Hoy (${escapeHtml(resumen.fecha || '')}): sin mensajes contabilizados aún${fuente}.`;
    return;
  }
  box.innerHTML = `<strong>Hoy ${escapeHtml(resumen.fecha)}:</strong> ${resumen.total_cliente} mensaje(s) al cliente${fuente} · `
    + locales.map(l => `${escapeHtml(l.local)}: <strong>${l.total_cliente}</strong>`).join(' · ');
}

async function cargarHistorialBd() {
  const cont = document.getElementById('wa-historial-bd');
  if (!cont) return;
  try {
    const res = await fetch('/api/envios-whatsapp/historial?limit=50');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al cargar historial');
    if (data.db) {
      const m = document.getElementById('wa-db-motor');
      const d = document.getElementById('wa-db-detalle');
      const b = document.getElementById('wa-db-badge');
      if (m) m.textContent = data.db.motor || 'BD';
      if (d) d.textContent = data.db.detalle || '';
      if (b) b.textContent = `💾 BD: ${data.db.motor || 'OK'}`;
    }
    const items = data.items || [];
    if (!items.length) {
      cont.innerHTML = 'Aún no hay reprogramaciones guardadas. Genere mensajes para guardar en la base de datos.';
      return;
    }
    cont.innerHTML = `
      <table class="w-full text-left">
        <thead><tr class="text-slate-400 border-b">
          <th class="py-1 pr-2">Fecha</th><th class="py-1 pr-2">Local</th><th class="py-1 pr-2">Cliente</th>
          <th class="py-1 pr-2">Factura</th><th class="py-1">Estado</th>
        </tr></thead>
        <tbody>
          ${items.map(it => `<tr class="border-b border-slate-50">
            <td class="py-1 pr-2 whitespace-nowrap">${escapeHtml(it.fecha || '')} ${escapeHtml(it.hora || '')}</td>
            <td class="py-1 pr-2">${escapeHtml(it.local || '')}</td>
            <td class="py-1 pr-2"><strong>${escapeHtml(it.nombre || '')}</strong></td>
            <td class="py-1 pr-2">${escapeHtml(it.factura || '')}</td>
            <td class="py-1">${escapeHtml(it.estado || '')}</td>
          </tr>`).join('')}
        </tbody>
      </table>
      <p class="mt-2 text-slate-400">Mostrando ${items.length} de ${data.total || items.length} registro(s).</p>`;
  } catch (e) {
    cont.textContent = 'No se pudo cargar el historial: ' + e.message;
  }
}

function actualizarModoUI() {
  const aviso = document.getElementById('wa-modo-aviso');
  const radioBusiness = document.getElementById('wa-modo-business');
  if (!businessApiActiva) {
    if (radioBusiness) radioBusiness.disabled = true;
    document.getElementById('wa-modo-wame').checked = true;
    aviso.classList.remove('hidden');
    aviso.textContent = 'WhatsApp Business API no configurada — solo wa.me.';
  } else {
    if (radioBusiness) radioBusiness.disabled = false;
    aviso.classList.add('hidden');
  }
}

function actualizarBadges(cfg) {
  const badge = document.getElementById('wa-api-badge');
  const smtp = document.getElementById('wa-smtp-badge');
  if (badge) {
    if (cfg?.business_api_activa) {
      badge.className = 'wa-api-badge wa-api-on';
      badge.textContent = `✅ Business API (${cfg.api_version || ''})`;
    } else {
      badge.className = 'wa-api-badge wa-api-off';
      badge.textContent = '⚠️ Business API no configurada';
    }
  }
  if (smtp) {
    if (cfg?.smtp_activo) {
      smtp.className = 'wa-api-badge wa-api-on';
      smtp.textContent = '✅ SMTP listo';
    } else {
      smtp.className = 'wa-api-badge wa-api-off';
      smtp.textContent = '✉️ Correo: copiar / mailto';
    }
  }
  document.getElementById('correo-hint').textContent = cfg?.smtp_activo
    ? 'Puede enviar por SMTP o abrir el cliente de correo.'
    : 'Configure SMTP en Render o use «Abrir en cliente de correo» / copiar.';
}

async function cargarConfigApi() {
  try {
    const res = await fetch('/api/envios-whatsapp/config');
    const data = await res.json();
    businessApiActiva = !!data.business_api_activa;
    smtpActivo = !!data.smtp_activo;
    actualizarBadges(data);
    if (businessApiActiva) document.getElementById('wa-modo-business').checked = true;
  } catch {
    businessApiActiva = !!window.WA_BUSINESS_ACTIVA;
    smtpActivo = !!window.SMTP_ACTIVO;
    actualizarBadges({ business_api_activa: businessApiActiva, smtp_activo: smtpActivo });
  }
  actualizarModoUI();
}

function renderTabla() {
  const cont = document.getElementById('wa-tabla');
  if (!itemsEnvio.length) {
    cont.className = 'wa-tabla-wrap text-sm text-slate-500 py-8 text-center';
    cont.innerHTML = contactos.length
      ? `${contactos.length} fila(s) listas — pulse <strong>Generar mensajes</strong>.`
      : 'Cargue la matriz y genere los mensajes.';
    return;
  }

  cont.className = 'wa-tabla-wrap';
  cont.innerHTML = `
    <table class="wa-tabla">
      <thead>
        <tr>
          <th>#</th><th>Cliente</th><th>Local</th><th>Producto</th><th>Factura</th><th>Estado</th>
        </tr>
      </thead>
      <tbody>
        ${itemsEnvio.map(it => {
          let estado = '<span class="wa-badge wa-badge-pendiente">Pendiente</span>';
          let rowClass = itemSeleccionado?.indice === it.indice ? 'seleccionado' : '';
          if (!it.valido) {
            estado = `<span class="wa-badge wa-badge-error">${escapeHtml(it.error || 'Sin WA')}</span>`;
            rowClass += ' invalido';
          } else if (it._enviado) {
            estado = '<span class="wa-badge wa-badge-enviado">Enviado</span>';
            rowClass += ' enviado';
          }
          return `<tr class="${rowClass.trim()}" data-idx="${it.indice}" style="cursor:pointer">
            <td>${it.indice}</td>
            <td><strong>${escapeHtml(it.nombre)}</strong><br><span class="text-xs text-slate-500">${escapeHtml(it.telefono || '—')}</span></td>
            <td>${escapeHtml(it.local || '—')}</td>
            <td>${escapeHtml(it.producto || '—')}</td>
            <td>${escapeHtml(it.factura || it.orden || '—')}</td>
            <td>${estado}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;

  cont.querySelectorAll('tr[data-idx]').forEach(tr => {
    tr.addEventListener('click', () => {
      const idx = Number(tr.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (it) seleccionarItem(it);
    });
  });
}

function seleccionarItem(it) {
  itemSeleccionado = refrescarMensajesItem({ ...it });
  // Preview = mensaje recompuesto en el navegador (emojis correctos)
  document.getElementById('preview-cliente').value = itemSeleccionado.mensaje_cliente || '';
  document.getElementById('preview-tienda').value = itemSeleccionado.mensaje_tienda || '';
  document.getElementById('btn-mark-cliente').disabled = !itemSeleccionado.valido && !itemSeleccionado.nombre;

  const btnCli = document.getElementById('btn-wa-cliente');
  const telCli = (window.WaEmoji && WaEmoji.limpiarTelefonoEC(itemSeleccionado.telefono_limpio || itemSeleccionado.telefono || ''))
    || String(itemSeleccionado.telefono || '').replace(/\D/g, '');
  if (btnCli) {
    if (telCli && itemSeleccionado.mensaje_cliente) {
      btnCli.disabled = false;
      btnCli.classList.remove('opacity-40', 'pointer-events-none');
    } else {
      btnCli.disabled = true;
      btnCli.classList.add('opacity-40', 'pointer-events-none');
    }
  }

  const btnTi = document.getElementById('btn-wa-tienda');
  if (btnTi) {
    if (itemSeleccionado.wa_link_tienda && itemSeleccionado.mensaje_tienda) {
      btnTi.disabled = false;
      btnTi.classList.remove('opacity-40', 'pointer-events-none');
    } else {
      btnTi.disabled = true;
      btnTi.classList.add('opacity-40', 'pointer-events-none');
    }
  }

  const sel = document.getElementById('correo-local');
  if (sel && itemSeleccionado.local) {
    const opt = [...sel.options].find(o => o.value === itemSeleccionado.local);
    if (opt) {
      sel.value = itemSeleccionado.local;
      mostrarCorreoLocal(itemSeleccionado.local);
    }
  }
  if (itemSeleccionado.email_tienda) document.getElementById('correo-email').value = itemSeleccionado.email_tienda;
  renderTabla();
}

function llenarSelectCorreos() {
  const sel = document.getElementById('correo-local');
  if (!sel) return;
  sel.innerHTML = correosPorLocal.map(c =>
    `<option value="${escapeHtml(c.local)}">${escapeHtml(c.local)} (${c.total_matriz})</option>`
  ).join('') || '<option value="">—</option>';
  if (correosPorLocal.length) {
    sel.value = correosPorLocal[0].local;
    mostrarCorreoLocal(correosPorLocal[0].local);
  }
}

function mostrarCorreoLocal(local) {
  const c = correosPorLocal.find(x => x.local === local);
  if (!c) return;
  document.getElementById('correo-asunto').value = c.asunto || '';
  document.getElementById('preview-correo').value = c.cuerpo || '';
  if (c.email_tienda) document.getElementById('correo-email').value = c.email_tienda;
  actualizarMailto();
}

function actualizarMailto() {
  const email = document.getElementById('correo-email').value.trim();
  const asunto = document.getElementById('correo-asunto').value.trim();
  const cuerpo = document.getElementById('preview-correo').value;
  const a = document.getElementById('btn-mailto');
  if (email && cuerpo) {
    a.href = `mailto:${encodeURIComponent(email).replace(/%40/g, '@')}?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`;
    a.classList.remove('opacity-40', 'pointer-events-none');
  } else {
    a.href = '#';
    a.classList.add('opacity-40', 'pointer-events-none');
  }
}

async function cargarExcel() {
  const input = document.getElementById('wa-excel');
  const file = input?.files?.[0];
  if (!file) { toast('Seleccione un archivo Excel o CSV', 'info'); return; }

  const fd = new FormData();
  fd.append('archivo', file);
  document.getElementById('wa-estado').textContent = 'Leyendo matriz…';

  const res = await fetch('/api/envios-whatsapp/subir-excel', { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al leer Excel');

  contactos = data.contactos || [];
  itemsEnvio = [];
  correosPorLocal = [];
  itemSeleccionado = null;
  document.getElementById('wa-resumen-contactos').innerHTML =
    `✅ <strong>${data.total}</strong> fila(s) · Columnas: ${escapeHtml((data.columnas_detectadas || []).join(', '))}`;

  const adv = document.getElementById('wa-advertencias');
  if (data.advertencias?.length) {
    adv.classList.remove('hidden');
    adv.innerHTML = '⚠️ ' + data.advertencias.map(escapeHtml).join('<br>');
  } else {
    adv.classList.add('hidden');
  }

  document.getElementById('wa-estado').textContent = `${data.total} filas`;
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`${data.total} filas cargadas de la matriz`, 'ok');
}

async function generarMensajes() {
  if (!contactos.length) return;
  const res = await fetch('/api/envios-whatsapp/generar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadBase(true)),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al generar');

  itemsEnvio = (data.items || []).map(it => {
    const row = { ...it, _enviado: false };
    return refrescarMensajesItem(row);
  });
  correosPorLocal = data.correos || [];
  document.getElementById('wa-estado').textContent = `${data.validos} WA listos`;
  llenarSelectCorreos();
  pintarResumenDia(data.resumen_dia);
  if (itemsEnvio.length) seleccionarItem(itemsEnvio[0]);
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`✨ ${data.total} mensajes generados y guardados en BD · ${correosPorLocal.length} correo(s) por local`, 'ok');
  cargarHistorialBd();
}

async function exportarExcel() {
  const res = await fetch('/api/envios-whatsapp/exportar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadBase(false)),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Error al exportar');
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `entregas_reprogramadas_${Date.now()}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
  toast('Excel exportado', 'ok');
}

async function marcarEnviadoCliente() {
  if (!itemSeleccionado) return;
  const res = await fetch('/api/envios-whatsapp/marcar-enviado', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      local: itemSeleccionado.local,
      nombre: itemSeleccionado.nombre,
      producto: itemSeleccionado.producto,
      factura: itemSeleccionado.factura || itemSeleccionado.orden,
      telefono: itemSeleccionado.telefono,
      canal: 'cliente',
      estado: 'Mensaje enviado',
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error');
  itemSeleccionado._enviado = true;
  const global = itemsEnvio.find(x => x.indice === itemSeleccionado.indice);
  if (global) global._enviado = true;
  pintarResumenDia(data.resumen_dia);
  actualizarKpis();
  renderTabla();
  toast('✅ Marcado como enviado y guardado en BD', 'ok');
  cargarHistorialBd();
}

async function enviarSmtp() {
  const email = document.getElementById('correo-email').value.trim();
  const asunto = document.getElementById('correo-asunto').value.trim();
  const cuerpo = document.getElementById('preview-correo').value;
  const local = document.getElementById('correo-local').value;
  if (!cuerpo) { toast('Genere los mensajes primero', 'info'); return; }

  const res = await fetch('/api/envios-whatsapp/enviar-correo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ local, asunto, cuerpo, email_tienda: email }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al enviar');

  if (data.modo === 'mailto' && data.mailto) {
    window.location.href = data.mailto;
    toast('Abriendo cliente de correo…', 'ok');
  } else {
    toast(`✅ Correo enviado a ${email}`, 'ok');
  }
}

function copiarTexto(id) {
  const el = document.getElementById(id);
  if (!el?.value) { toast('Nada que copiar', 'info'); return; }
  navigator.clipboard.writeText(el.value).then(
    () => toast('📋 Copiado', 'ok'),
    () => toast('No se pudo copiar', 'error'),
  );
}

/* —— Envío masivo clientes —— */
function abrirModalEnvio() {
  const pendientes = itemsEnvio.filter(i => i.valido && !i._enviado);
  if (!pendientes.length) {
    toast('No hay clientes pendientes con WhatsApp válido', 'info');
    return;
  }
  colaEnvio = pendientes;
  indiceCola = 0;
  document.getElementById('modal-envio').classList.remove('hidden');
  mostrarContactoCola();
}

function cerrarModalEnvio() {
  document.getElementById('modal-envio').classList.add('hidden');
  clearTimeout(autoTimer);
  enviandoBusiness = false;
}

function actualizarModalBotones() {
  const esBusiness = modoEnvio() === 'business' && businessApiActiva;
  const linkWa = document.getElementById('modal-abrir-wa');
  const btnBusiness = document.getElementById('modal-enviar-business');
  const titulo = document.getElementById('modal-titulo');
  if (esBusiness) {
    titulo.textContent = '📱 Envío Business — cliente';
    linkWa.classList.add('hidden');
    btnBusiness.classList.remove('hidden');
  } else {
    titulo.textContent = '📤 Envío masivo al cliente';
    linkWa.classList.remove('hidden');
    btnBusiness.classList.add('hidden');
  }
}

function mostrarContactoCola() {
  if (indiceCola >= colaEnvio.length) {
    toast('🎉 Envío masivo completado', 'ok');
    cerrarModalEnvio();
    return;
  }
  actualizarModalBotones();
  const it = colaEnvio[indiceCola];
  const total = colaEnvio.length;
  document.getElementById('modal-progreso').textContent = `Contacto ${indiceCola + 1} de ${total}`;
  document.getElementById('modal-barra').style.width = `${Math.round((indiceCola / total) * 100)}%`;
  document.getElementById('modal-nombre').textContent = it.nombre;
  document.getElementById('modal-telefono').textContent = it.telefono;
  refrescarMensajesItem(it);
  const msgCli = it.mensaje_cliente || it.mensaje || '';
  const telCli = it.telefono_limpio || it.telefono || '';
  document.getElementById('modal-preview').textContent = msgCli;

  const esBusiness = modoEnvio() === 'business' && businessApiActiva;
  if (!esBusiness) {
    // No auto-abrir con ?text= (rompe emojis). Solo abre chat + copia en gesto del usuario.
    // En envío masivo: copiar y abrir chat vacío; el asesor pega y confirma.
    abrirWhatsApp(telCli, msgCli);
    if (document.getElementById('wa-auto-siguiente')?.checked) {
      clearTimeout(autoTimer);
      autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 8000);
    }
  } else if (document.getElementById('wa-auto-siguiente')?.checked && !enviandoBusiness) {
    enviarPorBusiness(it).then(ok => {
      if (ok) autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 2000);
    });
  }
}

async function enviarPorBusiness(it) {
  if (enviandoBusiness) return false;
  enviandoBusiness = true;
  const btn = document.getElementById('modal-enviar-business');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Enviando…'; }
  try {
    refrescarMensajesItem(it);
    const res = await fetch('/api/envios-whatsapp/enviar-business', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({
        item: {
          indice: it.indice,
          telefono_limpio: it.telefono_limpio,
          mensaje: it.mensaje_cliente || it.mensaje,
        },
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error');
    if (data.ok) {
      toast(`✅ Enviado a ${it.nombre}`, 'ok');
      return true;
    }
    toast(data.error || 'No se pudo enviar', 'error');
    return false;
  } catch (e) {
    toast(e.message, 'error');
    return false;
  } finally {
    enviandoBusiness = false;
    if (btn) { btn.disabled = false; btn.textContent = '📱 Enviar por Business API'; }
  }
}

async function marcarEnviadoYSiguiente() {
  clearTimeout(autoTimer);
  const it = colaEnvio[indiceCola];
  if (it) {
    const global = itemsEnvio.find(x => x.indice === it.indice);
    if (global) global._enviado = true;
    try {
      const res = await fetch('/api/envios-whatsapp/marcar-enviado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          local: it.local,
          nombre: it.nombre,
          producto: it.producto,
          factura: it.factura || it.orden,
          telefono: it.telefono,
          canal: 'cliente',
          estado: 'Mensaje enviado',
        }),
      });
      const data = await res.json();
      if (res.ok) pintarResumenDia(data.resumen_dia);
    } catch { /* ignore */ }
  }
  indiceCola += 1;
  actualizarKpis();
  renderTabla();
  mostrarContactoCola();
}

function saltarContacto() {
  clearTimeout(autoTimer);
  indiceCola += 1;
  mostrarContactoCola();
}

/* —— Tabs —— */
document.querySelectorAll('.wa-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.wa-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const name = tab.dataset.tab;
    document.getElementById('panel-cliente').classList.toggle('hidden', name !== 'cliente');
    document.getElementById('panel-tienda').classList.toggle('hidden', name !== 'tienda');
    document.getElementById('panel-correo').classList.toggle('hidden', name !== 'correo');
  });
});

document.getElementById('btn-recargar-historial')?.addEventListener('click', () =>
  cargarHistorialBd().catch(e => toast(e.message, 'error')));
document.getElementById('btn-cargar-excel')?.addEventListener('click', () =>
  cargarExcel().catch(e => toast(e.message, 'error')));
document.getElementById('btn-generar')?.addEventListener('click', () =>
  generarMensajes().catch(e => toast(e.message, 'error')));
document.getElementById('btn-exportar')?.addEventListener('click', () =>
  exportarExcel().catch(e => toast(e.message, 'error')));
document.getElementById('btn-enviar-masivo')?.addEventListener('click', abrirModalEnvio);
document.getElementById('btn-copy-cliente')?.addEventListener('click', () => copiarTexto('preview-cliente'));
document.getElementById('btn-copy-tienda')?.addEventListener('click', () => copiarTexto('preview-tienda'));
document.getElementById('btn-copy-correo')?.addEventListener('click', () => copiarTexto('preview-correo'));
document.getElementById('btn-wa-cliente')?.addEventListener('click', (e) => {
  e.preventDefault();
  abrirWaClienteDesdePreview();
});
document.getElementById('btn-wa-tienda')?.addEventListener('click', (e) => {
  e.preventDefault();
  abrirWaTiendaDesdePreview();
});
document.getElementById('modal-abrir-wa')?.addEventListener('click', async (e) => {
  e.preventDefault();
  const it = colaEnvio[indiceCola];
  if (!it) return;
  refrescarMensajesItem(it);
  await abrirWhatsApp(it.telefono_limpio || it.telefono, it.mensaje_cliente || it.mensaje);
});
document.getElementById('btn-mark-cliente')?.addEventListener('click', () =>
  marcarEnviadoCliente().catch(e => toast(e.message, 'error')));
document.getElementById('btn-enviar-smtp')?.addEventListener('click', () =>
  enviarSmtp().catch(e => toast(e.message, 'error')));
document.getElementById('correo-local')?.addEventListener('change', e => mostrarCorreoLocal(e.target.value));
document.getElementById('correo-email')?.addEventListener('input', actualizarMailto);
document.getElementById('correo-asunto')?.addEventListener('input', actualizarMailto);
document.getElementById('preview-correo')?.addEventListener('input', actualizarMailto);
document.getElementById('modal-enviado')?.addEventListener('click', () => marcarEnviadoYSiguiente());
document.getElementById('modal-saltar')?.addEventListener('click', saltarContacto);
document.getElementById('modal-cerrar')?.addEventListener('click', cerrarModalEnvio);
document.getElementById('modal-enviar-business')?.addEventListener('click', async () => {
  const it = colaEnvio[indiceCola];
  if (!it) return;
  const ok = await enviarPorBusiness(it);
  if (ok) marcarEnviadoYSiguiente();
});
document.getElementById('wa-modo-business')?.addEventListener('change', actualizarModoUI);
document.getElementById('wa-modo-wame')?.addEventListener('change', actualizarModoUI);

actualizarBotones();
actualizarKpis();
cargarConfigApi();
if (window.RESUMEN_DIA_INICIAL) pintarResumenDia(window.RESUMEN_DIA_INICIAL);
cargarHistorialBd();
