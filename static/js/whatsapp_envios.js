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
  if (!locales.length) {
    box.innerHTML = `Hoy (${escapeHtml(resumen.fecha || '')}): sin mensajes contabilizados aún.`;
    return;
  }
  box.innerHTML = `<strong>Hoy ${escapeHtml(resumen.fecha)}:</strong> ${resumen.total_cliente} mensaje(s) al cliente · `
    + locales.map(l => `${escapeHtml(l.local)}: <strong>${l.total_cliente}</strong>`).join(' · ');
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
  itemSeleccionado = it;
  document.getElementById('preview-cliente').value = it.mensaje_cliente || it.mensaje || '';
  document.getElementById('preview-tienda').value = it.mensaje_tienda || '';
  document.getElementById('btn-mark-cliente').disabled = !it.valido && !it.nombre;

  const linkCli = document.getElementById('btn-wa-cliente');
  const waCli = it.wa_link_cliente || it.wa_link || '';
  if (waCli) {
    linkCli.href = waCli;
    linkCli.classList.remove('opacity-40', 'pointer-events-none');
  } else {
    linkCli.href = '#';
    linkCli.classList.add('opacity-40', 'pointer-events-none');
  }

  const linkTi = document.getElementById('btn-wa-tienda');
  if (it.wa_link_tienda) {
    linkTi.href = it.wa_link_tienda;
    linkTi.classList.remove('opacity-40', 'pointer-events-none');
  } else {
    linkTi.href = '#';
    linkTi.classList.add('opacity-40', 'pointer-events-none');
  }

  const sel = document.getElementById('correo-local');
  if (sel && it.local) {
    const opt = [...sel.options].find(o => o.value === it.local);
    if (opt) {
      sel.value = it.local;
      mostrarCorreoLocal(it.local);
    }
  }
  if (it.email_tienda) document.getElementById('correo-email').value = it.email_tienda;
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

  itemsEnvio = (data.items || []).map(it => ({ ...it, _enviado: false }));
  correosPorLocal = data.correos || [];
  document.getElementById('wa-estado').textContent = `${data.validos} WA listos`;
  llenarSelectCorreos();
  pintarResumenDia(data.resumen_dia);
  if (itemsEnvio.length) seleccionarItem(itemsEnvio[0]);
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`✨ ${data.total} mensajes generados · ${correosPorLocal.length} correo(s) por local · contados en el día`, 'ok');
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
  toast('✅ Marcado como enviado y contabilizado', 'ok');
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
  document.getElementById('modal-preview').textContent = it.mensaje_cliente || it.mensaje;
  document.getElementById('modal-abrir-wa').href = it.wa_link_cliente || it.wa_link;

  const esBusiness = modoEnvio() === 'business' && businessApiActiva;
  if (!esBusiness) {
    window.open(it.wa_link_cliente || it.wa_link, '_blank', 'noopener');
    if (document.getElementById('wa-auto-siguiente')?.checked) {
      clearTimeout(autoTimer);
      autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 5000);
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
    const res = await fetch('/api/envios-whatsapp/enviar-business', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
