/**
 * Reprogramación de entregas — cliente / tienda / correo + contador diario
 */
let contactosGlobales = [];
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
  // Siempre prellenar el texto en el enlace para enviar más rápido
  const result = await WaEmoji.abrirWhatsAppSeguro(telefono, mensaje, { modo: 'prefill' });
  if (!result.ok) {
    toast(result.error || 'No se pudo abrir WhatsApp', 'error');
    return false;
  }
  toast(
    result.copiado
      ? 'WhatsApp abierto con texto prellenado. Solo pulsa Enviar en el chat.'
      : 'WhatsApp abierto.',
    'ok',
  );
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

/** WA tienda: usa el número exacto del local resuelto en el backend */
async function abrirWaTiendaDesdePreview() {
  const it = itemSeleccionado;
  if (!it) {
    toast('Seleccione un contacto de la tabla', 'info');
    return;
  }
  refrescarMensajesItem(it);
  const mensaje = it.mensaje_tienda;
  document.getElementById('preview-tienda').value = mensaje;

  const localNombre = (it.local || '').trim();
  let tel = '';

  // 1) Número ya resuelto por el backend (fuente de verdad)
  if (it.wa_numero_tienda) {
    tel = String(it.wa_numero_tienda).replace(/\D/g, '');
  }

  // 2) Resolver desde TIENDAS_WA_MAP en tiempo real (si el backend no lo incluyó)
  if (!tel && window.WaEmoji && WaEmoji.resolverWaTienda) {
    const resuelto = WaEmoji.resolverWaTienda(localNombre);
    tel = resuelto ? String(resuelto).replace(/\D/g, '') : '';
  }

  if (!tel) {
    toast(`Sin número registrado para: "${localNombre}". Verifica el nombre del local en la matriz.`, 'error');
    return;
  }

  toast(`Abriendo WhatsApp de "${localNombre}" → ${tel}`, 'info');
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
          <th>#</th><th>Cliente</th><th>Local</th><th>Producto</th><th>OT / Factura</th><th>Estado</th><th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        ${itemsEnvio.map(it => {
          let estado = '<span class="wa-badge wa-badge-pendiente">Pendiente</span>';
          let rowClass = itemSeleccionado?.indice === it.indice ? 'seleccionado' : '';
          const nombreDisplay = it.nombre_completo || it.nombre || '\u2014';
          if (!it.valido) {
            estado = `<span class="wa-badge wa-badge-error">${escapeHtml(it.error || 'Sin WA')}</span>`;
            rowClass += ' invalido';
          } else if (it._enviado) {
            estado = '<span class="wa-badge wa-badge-enviado">\u2705 Enviado</span>';
            rowClass += ' enviado';
          }

          const btnCliente = it.valido && !it._enviado
            ? `<button class="wa-btn-mini wa-btn-send-cli" data-idx="${it.indice}" title="Enviar al cliente">\ud83d\udcf1 Cliente</button>`
            : (it._enviado ? '<span class="text-xs" style="color:#059669">\u2705</span>' : '');
          const btnTienda = it.wa_numero_tienda
            ? `<button class="wa-btn-mini wa-btn-send-ti" data-idx="${it.indice}" title="Enviar a tienda">\ud83c\udfea Tienda</button>`
            : '';
          const btnMark = it.valido && !it._enviado
            ? `<button class="wa-btn-mini wa-btn-mark" data-idx="${it.indice}" title="Marcar como enviado">\u2705</button>`
            : '';
          const btnCombo = it.valido && !it._enviado
            ? `<button class="wa-btn-mini wa-btn-combo" data-idx="${it.indice}" title="Enviar + Marcar enviado">\ud83d\ude80</button>`
            : '';

          return `<tr class="${rowClass.trim()}" data-idx="${it.indice}" style="cursor:pointer">
            <td>${it.indice}</td>
            <td><strong>${escapeHtml(nombreDisplay)}</strong><br><span class="text-xs text-slate-500">${escapeHtml(it.telefono || '\u2014')}</span></td>
            <td>${escapeHtml(it.local || '\u2014')}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(it.producto || '\u2014')}</td>
            <td>${escapeHtml(it.orden || it.factura || '\u2014')}</td>
            <td>${estado}</td>
            <td style="white-space:nowrap">${btnCombo} ${btnCliente} ${btnTienda} ${btnMark}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;

  // Evento: seleccionar fila
  cont.querySelectorAll('tr[data-idx]').forEach(tr => {
    tr.addEventListener('click', (e) => {
      if (e.target.closest('button')) return;
      const idx = Number(tr.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (it) seleccionarItem(it);
    });
  });

  // Evento: botón enviar a cliente
  cont.querySelectorAll('.wa-btn-send-cli').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const idx = Number(btn.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (!it) return;
      refrescarMensajesItem(it);
      const tel = it.telefono_limpio || it.telefono || '';
      const ok = await abrirWhatsApp(tel, it.mensaje_cliente || it.mensaje);
      if (ok) {
        btn.textContent = '\u2705';
        btn.disabled = true;
      }
    });
  });

  // Evento: botón enviar a tienda
  cont.querySelectorAll('.wa-btn-send-ti').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const idx = Number(btn.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (!it) return;
      refrescarMensajesItem(it);
      const tel = it.wa_numero_tienda || '';
      if (!tel) { toast('Sin número de tienda', 'error'); return; }
      const ok = await abrirWhatsApp(tel, it.mensaje_tienda);
      if (ok) {
        btn.textContent = '\u2705';
        btn.disabled = true;
      }
    });
  });

  // Evento: marcar como enviado (y avanzar si envío rápido activo)
  cont.querySelectorAll('.wa-btn-mark').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const idx = Number(btn.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (!it) return;
      toast(`✅ #${it.indice} marcado como enviado`, 'ok');
      await marcarYSiguiente(it);
    });
  });

  // Evento: combo enviar cliente + marcar como enviado en un solo clic
  cont.querySelectorAll('.wa-btn-combo').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const idx = Number(btn.dataset.idx);
      const it = itemsEnvio.find(x => x.indice === idx);
      if (!it) return;
      refrescarMensajesItem(it);
      const tel = it.telefono_limpio || it.telefono || '';
      const ok = await abrirWhatsApp(tel, it.mensaje_cliente || it.mensaje);
      if (ok) {
        await marcarYSiguiente(it);
      }
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

  contactosGlobales = data.contactos || [];
  
  document.getElementById('wa-resumen-contactos').innerHTML =
    `✅ <strong>${data.total}</strong> fila(s) maestras leídas · Columnas: ${escapeHtml((data.columnas_detectadas || []).join(', '))}`;

  const adv = document.getElementById('wa-advertencias');
  if (data.advertencias?.length) {
    adv.classList.remove('hidden');
    adv.innerHTML = '⚠️ ' + data.advertencias.map(escapeHtml).join('<br>');
  } else {
    adv.classList.add('hidden');
  }

  // Extract unique dates for the filter
  const fechasUnicas = [...new Set(contactosGlobales.map(c => c.fecha_reprogramada).filter(Boolean))].sort();
  const filtroContainer = document.getElementById('wa-filtro-container');
  const selectFecha = document.getElementById('wa-filtro-fecha');
  
  if (fechasUnicas.length > 0) {
    selectFecha.innerHTML = '<option value="">Todas las fechas</option>' + 
      fechasUnicas.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join('');
    filtroContainer.classList.remove('hidden');
  } else {
    filtroContainer.classList.add('hidden');
    selectFecha.innerHTML = '';
  }

  aplicarFiltroFecha(); // This will populate `contactos`
  
  toast(`${data.total} filas cargadas de la matriz`, 'ok');
}

async function cargarUltimaMatriz() {
  try {
    const res = await fetch('/api/envios-whatsapp/ultima-matriz');
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.contactos) return;
    
    contactosGlobales = data.contactos || [];
    
    document.getElementById('wa-resumen-contactos').innerHTML =
      `✅ <strong>${data.total}</strong> fila(s) maestras recuperadas · Columnas: ${escapeHtml((data.columnas_detectadas || []).join(', '))}`;

    const adv = document.getElementById('wa-advertencias');
    if (data.advertencias?.length) {
      adv.classList.remove('hidden');
      adv.innerHTML = '⚠️ ' + data.advertencias.map(escapeHtml).join('<br>');
    } else {
      adv.classList.add('hidden');
    }

    const fechasUnicas = [...new Set(contactosGlobales.map(c => c.fecha_reprogramada).filter(Boolean))].sort();
    const filtroContainer = document.getElementById('wa-filtro-container');
    const selectFecha = document.getElementById('wa-filtro-fecha');
    
    if (fechasUnicas.length > 0) {
      selectFecha.innerHTML = '<option value="">Todas las fechas</option>' + 
        fechasUnicas.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join('');
      filtroContainer.classList.remove('hidden');
    } else {
      filtroContainer.classList.add('hidden');
      selectFecha.innerHTML = '';
    }

    aplicarFiltroFecha();
  } catch (e) {
    console.error("No se pudo cargar la ultima matriz", e);
  }
}

/* ==========================================================================
   MÓDULO INDEPENDIENTE: CONTROL DE OT Y VALIDADOR DE REPROGRAMACIONES
   ========================================================================== */
let reprogramacionesValidadorData = [];

function inicializarValidadorOTs() {
  const fileInput = document.getElementById('validador-excel-file');
  if (!fileInput) return;

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
      try {
        if (!window.XLSX) {
          toast('SheetJS no disponible para leer el archivo', 'error');
          return;
        }

        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array', cellDates: true });
        
        // Buscar la hoja "CONTROL OT"
        let sheetName = 'CONTROL OT';
        if (!workbook.SheetNames.includes(sheetName)) {
          sheetName = workbook.SheetNames.find(n => n.toUpperCase().includes('CONTROL') || n.toUpperCase().includes('OT')) || workbook.SheetNames[0];
        }

        if (!sheetName) {
          toast('No se encontró la hoja "CONTROL OT" en el archivo.', 'error');
          return;
        }

        const worksheet = workbook.Sheets[sheetName];
        // Según el análisis previo, los datos reales comienzan en la fila 7 (índice 6)
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { range: 6, raw: false, dateNF: 'yyyy-mm-dd' });
        
        procesarDatosValidador(jsonData, file.name);

      } catch (error) {
        console.error("Error al leer Excel de control:", error);
        toast("Error al procesar el archivo Excel de control.", "error");
      }
    };
    reader.readAsArrayBuffer(file);
  });
}

function procesarDatosValidador(data, fileName = '') {
  const otMap = new Map();

  // Paso 1: Agrupar todas las filas por su número de OT
  data.forEach(row => {
    const otKey = Object.keys(row).find(key => key.trim().toUpperCase() === 'OT');
    if (otKey && row[otKey]) {
      const otValue = String(row[otKey]).trim();
      if (otValue !== "") {
        if (!otMap.has(otValue)) {
          otMap.set(otValue, []);
        }
        otMap.get(otValue).push(row);
      }
    }
  });

  // Paso 2: Filtrar analizando LA FECHA DE ENTREGA PROGRAMADA
  reprogramacionesValidadorData = [];

  // Función auxiliar para formatear fechas (idéntica a la tuya)
  const formatearFecha = (val) => {
    if (!val) return null;
    if (val instanceof Date) {
      return val.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }
    return String(val).split('T')[0].trim();
  };

  otMap.forEach((records, ot) => {
    if (records.length > 1) {
      const findKey = (row, keyword) => Object.keys(row).find(k => k.toLowerCase().includes(keyword.toLowerCase()));

      let fechasUnicas = [];

      // Extraer todas las fechas programadas de esta OT en orden
      records.forEach(rec => {
        const colFechaProg = findKey(rec, 'programada por indulentes') || findKey(rec, 'programada') || findKey(rec, 'fechan');
        if (colFechaProg && rec[colFechaProg]) {
          const fechaFmt = formatearFecha(rec[colFechaProg]);
          // Solo agregamos la fecha si es diferente a la última registrada en nuestro array
          // (Esto detecta cuando la fecha realmente CAMBIA)
          if (fechaFmt && (fechasUnicas.length === 0 || fechasUnicas[fechasUnicas.length - 1] !== fechaFmt)) {
            fechasUnicas.push(fechaFmt);
          }
        }
      });

      // Si hay MÁS DE UNA fecha diferente en el historial de esta OT, es una reprogramación real
      if (fechasUnicas.length > 1) {
        reprogramacionesValidadorData.push({
          ot: ot,
          cambiosTotales: fechasUnicas.length - 1,
          fechaAnterior: fechasUnicas[fechasUnicas.length - 2], // La penúltima fecha
          fechaNueva: fechasUnicas[fechasUnicas.length - 1],    // La última fecha
          records: records
        });
      }
    }
  });

  // Ordenar para mostrar primero las que tienen más cambios de fecha
  reprogramacionesValidadorData.sort((a, b) => b.cambiosTotales - a.cambiosTotales);

  // Renderizar la tabla de reprogramaciones
  renderTablaValidador();

  const uploadStatus = document.getElementById('validador-upload-status');
  const uploadStatusText = document.getElementById('validador-upload-status-text');
  const resultadoSection = document.getElementById('validador-resultado-section');

  if (uploadStatus && uploadStatusText) {
    uploadStatus.classList.remove('hidden');
    uploadStatusText.textContent = `Archivo cargado: ${fileName || 'Matriz_Control_OT_Reprogramaciones_ACTUALIZACION_AUTOMATICA.xlsx'} (${data.length} registros analizados)`;
  }

  if (resultadoSection) {
    resultadoSection.classList.remove('hidden');
  }

  toast(`Análisis completo. ${reprogramacionesValidadorData.length} OTs con cambio de fecha detectadas.`, 'ok');
}

function renderTablaValidador() {
  const tbody = document.getElementById('validador-table-body');
  const totalBadge = document.getElementById('total-validador-reprog');
  const emptyBox = document.getElementById('validador-empty-box');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (reprogramacionesValidadorData.length === 0) {
    if (totalBadge) {
      totalBadge.textContent = "0 encontradas";
      totalBadge.className = "glass-pill text-xs font-bold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 shrink-0";
    }
    tbody.parentElement.classList.add('hidden');
    if (emptyBox) emptyBox.classList.remove('hidden');
    return;
  }

  if (totalBadge) {
    totalBadge.textContent = `${reprogramacionesValidadorData.length} alertas`;
    totalBadge.className = "glass-pill text-xs font-bold px-3 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-200 shrink-0";
  }
  tbody.parentElement.classList.remove('hidden');
  if (emptyBox) emptyBox.classList.add('hidden');

  reprogramacionesValidadorData.forEach(item => {
    const tr = document.createElement('tr');

    // Determinar el nivel de alerta visual con badges estilo glass
    let alertaBadge = '';
    if (item.cambiosTotales > 1) {
      alertaBadge = `<span class="inline-flex items-center gap-1 bg-rose-50 text-rose-700 font-bold px-2.5 py-0.5 rounded-full border border-rose-200 text-xs">🔥 ¡${item.cambiosTotales + 1}ra Reprogramación!</span>`;
    } else {
      alertaBadge = `<span class="inline-flex items-center gap-1 bg-amber-50 text-amber-800 font-bold px-2.5 py-0.5 rounded-full border border-amber-200 text-xs">⏱️ Fecha Modificada</span>`;
    }

    // Generar mensaje para WhatsApp dinámicamente
    const msj = `Estimado cliente, le informamos que la entrega de su OT ${item.ot} ha sido reprogramada. La nueva fecha estimada es el ${item.fechaNueva}.`;
    const msjUrl = `https://wa.me/?text=${encodeURIComponent(msj)}`;

    tr.innerHTML = `
      <td><strong class="font-mono text-slate-800 text-sm font-bold tracking-tight">${escapeHtml(item.ot)}</strong></td>
      <td>${alertaBadge}</td>
      <td><span class="text-slate-400 line-through text-xs font-medium">${escapeHtml(item.fechaAnterior)}</span></td>
      <td><span class="font-bold text-blue-700 bg-blue-50/80 px-2.5 py-1 rounded-lg text-xs border border-blue-100/80 inline-block font-mono">${escapeHtml(item.fechaNueva)}</span></td>
      <td style="white-space:nowrap">
        <a href="${msjUrl}" target="_blank" class="btn-ola btn-ola--wa text-xs py-1 px-2.5 inline-flex items-center gap-1.5 shadow-sm">
          <span class="btn-ola__icon" style="width:1.25rem;height:1.25rem;font-size:0.75rem">💬</span>
          <span>Notificar</span>
        </a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function aplicarFiltroFecha() {
  const fechaSelect = document.getElementById('wa-filtro-fecha')?.value || '';
  if (fechaSelect) {
    contactos = contactosGlobales.filter(c => c.fecha_reprogramada === fechaSelect);
  } else {
    contactos = [...contactosGlobales];
  }
  
  itemsEnvio = [];
  correosPorLocal = [];
  itemSeleccionado = null;
  
  document.getElementById('wa-estado').textContent = `${contactos.length} filas`;
  actualizarBotones();
  actualizarKpis();
  renderTabla();
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

/* —— Envío masivo clientes (secuencial rápido) —— */
let envioRapidoActivo = false;

async function abrirModalEnvio() {
  const pendientes = itemsEnvio.filter(i => i.valido && !i._enviado);
  if (!pendientes.length) {
    toast('No hay clientes pendientes con WhatsApp válido', 'info');
    return;
  }

  const esBusiness = modoEnvio() === 'business' && businessApiActiva;

  if (esBusiness) {
    toast(`Enviando ${pendientes.length} mensajes por Business API...`, 'info');
    for (let it of pendientes) {
      const ok = await enviarPorBusiness(it);
      if (ok) {
        it._enviado = true;
        try {
          await fetch('/api/envios-whatsapp/marcar-enviado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              local: it.local, nombre: it.nombre_completo || it.nombre,
              producto: it.producto, factura: it.factura || it.orden,
              telefono: it.telefono, canal: 'cliente', estado: 'Mensaje enviado',
            })
          });
        } catch (e) {}
      }
    }
    toast('✅ Envío Business completado', 'ok');
  } else {
    // Activar modo envío rápido secuencial
    envioRapidoActivo = true;
    toast(`🚀 Envío rápido activado: ${pendientes.length} pendientes. Abriendo primer chat...`, 'info');
    await enviarYAvanzar(pendientes[0]);
  }

  actualizarKpis();
  renderTabla();
  cargarHistorialBd();
}

/** Abre WA del cliente, lo selecciona, hace scroll, y queda listo para marcar */
async function enviarYAvanzar(it) {
  if (!it) {
    envioRapidoActivo = false;
    toast('🎉 ¡Todos los mensajes enviados!', 'ok');
    actualizarKpis();
    renderTabla();
    return;
  }
  seleccionarItem(it);
  renderTabla();
  // Scroll a la fila
  const row = document.querySelector(`tr[data-idx="${it.indice}"]`);
  if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  // Abrir WA con texto prellenado
  refrescarMensajesItem(it);
  const tel = it.telefono_limpio || it.telefono || '';
  await abrirWhatsApp(tel, it.mensaje_cliente || it.mensaje);
}

/** Marca como enviado + avanza al siguiente automáticamente */
async function marcarYSiguiente(it) {
  it._enviado = true;
  // Guardar en BD en background
  fetch('/api/envios-whatsapp/marcar-enviado', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      local: it.local, nombre: it.nombre_completo || it.nombre,
      producto: it.producto, factura: it.factura || it.orden,
      telefono: it.telefono, canal: 'cliente', estado: 'Mensaje enviado',
    }),
  }).catch(() => {});

  actualizarKpis();
  renderTabla();

  if (envioRapidoActivo) {
    // Buscar siguiente pendiente
    const siguiente = itemsEnvio.find(i => i.valido && !i._enviado);
    const restantes = itemsEnvio.filter(i => i.valido && !i._enviado).length;
    if (siguiente) {
      toast(`✅ Enviado. Siguiente (${restantes} restantes)...`, 'ok');
      await enviarYAvanzar(siguiente);
    } else {
      envioRapidoActivo = false;
      toast('🎉 ¡Todos los mensajes enviados!', 'ok');
    }
  }
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
document.getElementById('wa-filtro-fecha')?.addEventListener('change', aplicarFiltroFecha);
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
cargarUltimaMatriz();
inicializarValidadorOTs();
