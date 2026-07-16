/**
 * Reprogramación de entregas — pedidos/órdenes + Excel + wa.me / Business API
 */

let contactos = [];
let itemsEnvio = [];
let colaEnvio = [];
let indiceCola = 0;
let autoTimer = null;
let businessApiActiva = false;
let enviandoBusiness = false;

const PLANTILLA_EJ = window.WA_PLANTILLA_EJEMPLO || '';

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

function payloadBase() {
  return {
    plantilla: document.getElementById('wa-plantilla').value.trim(),
    asesor: document.getElementById('wa-asesor').value.trim() || window.DEFAULT_ASESOR || '',
    incluir_pie: document.getElementById('wa-incluir-pie').checked,
    fecha_reprogramada: document.getElementById('wa-fecha-reprog')?.value.trim() || '',
    fecha_anterior: document.getElementById('wa-fecha-anterior')?.value.trim() || '',
    hora: document.getElementById('wa-hora')?.value.trim() || '',
    motivo: document.getElementById('wa-motivo')?.value.trim() || '',
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

function actualizarModoUI() {
  const esBusiness = modoEnvio() === 'business';
  const aviso = document.getElementById('wa-modo-aviso');
  const desc = document.getElementById('wa-modo-desc');
  const radioBusiness = document.getElementById('wa-modo-business');

  if (!businessApiActiva) {
    if (radioBusiness) radioBusiness.disabled = true;
    document.getElementById('wa-modo-wame').checked = true;
    aviso.classList.remove('hidden');
    aviso.textContent = 'WhatsApp Business API no configurada. Usa wa.me o agrega WHATSAPP_BUSINESS_TOKEN en Render.';
  } else {
    if (radioBusiness) radioBusiness.disabled = false;
    aviso.classList.add('hidden');
  }

  if (esBusiness && businessApiActiva) {
    desc.innerHTML = 'Los mensajes se envían automáticamente desde tu cuenta WhatsApp Business.'
      + ' <label class="inline-flex items-center gap-1.5 ml-2 cursor-pointer">'
      + '<input type="checkbox" id="wa-auto-siguiente" class="rounded text-green-600" '
      + (document.getElementById('wa-auto-siguiente')?.checked ? 'checked' : '') + '> '
      + 'Pausa automática 5s entre contactos</label>';
  } else {
    desc.innerHTML = 'El envío abre WhatsApp Web/App con cada mensaje listo. Confirma el envío y pasa al siguiente contacto.'
      + ' <label class="inline-flex items-center gap-1.5 ml-2 cursor-pointer">'
      + '<input type="checkbox" id="wa-auto-siguiente" class="rounded text-green-600" '
      + (document.getElementById('wa-auto-siguiente')?.checked ? 'checked' : '') + '> '
      + 'Pausa automática 5s entre contactos</label>';
  }
}

function actualizarBadgeApi(cfg) {
  const badge = document.getElementById('wa-api-badge');
  if (!badge) return;
  if (cfg?.business_api_activa) {
    badge.className = 'wa-api-badge wa-api-on';
    badge.textContent = `✅ Business API conectada (${cfg.api_version})`;
  } else {
    badge.className = 'wa-api-badge wa-api-off';
    badge.textContent = '⚠️ Business API no configurada — solo wa.me';
  }
}

async function cargarConfigApi() {
  try {
    const res = await fetch('/api/envios-whatsapp/config');
    const data = await res.json();
    businessApiActiva = !!data.business_api_activa;
    actualizarBadgeApi(data);
    if (businessApiActiva) {
      document.getElementById('wa-modo-business').checked = true;
    }
  } catch {
    businessApiActiva = !!window.WA_BUSINESS_ACTIVA;
    actualizarBadgeApi({ business_api_activa: businessApiActiva, api_version: 'v21.0' });
  }
  actualizarModoUI();
}

function renderTabla() {
  const cont = document.getElementById('wa-tabla');
  if (!itemsEnvio.length) {
    cont.className = 'wa-tabla-wrap text-sm text-slate-500 py-8 text-center';
    cont.innerHTML = contactos.length
      ? `${contactos.length} contacto(s) listos — pulsa <strong>Generar mensajes</strong>.`
      : 'Cargue un Excel y genere los mensajes para ver la lista.';
    return;
  }

  cont.className = 'wa-tabla-wrap';
  cont.innerHTML = `
    <table class="wa-tabla">
      <thead>
        <tr>
          <th>#</th><th>Nombre</th><th>Teléfono</th><th>Estado</th><th>Vista previa</th><th></th>
        </tr>
      </thead>
      <tbody>
        ${itemsEnvio.map(it => {
          let estado = '<span class="wa-badge wa-badge-pendiente">Pendiente</span>';
          let rowClass = '';
          if (!it.valido) {
            estado = `<span class="wa-badge wa-badge-error">${escapeHtml(it.error || 'Inválido')}</span>`;
            rowClass = 'invalido';
          } else if (it._enviado) {
            estado = '<span class="wa-badge wa-badge-enviado">Enviado</span>';
            rowClass = 'enviado';
          } else if (it._error_envio) {
            estado = `<span class="wa-badge wa-badge-error">${escapeHtml(it._error_envio)}</span>`;
            rowClass = 'invalido';
          }
          const prev = (it.mensaje || '').slice(0, 90) + ((it.mensaje || '').length > 90 ? '…' : '');
          const btn = it.valido && it.wa_link
            ? `<a href="${it.wa_link}" target="_blank" rel="noopener" class="text-xs font-bold text-green-700 hover:underline">Abrir WA</a>`
            : '—';
          return `<tr class="${rowClass}" data-idx="${it.indice}">
            <td>${it.indice}</td>
            <td><strong>${escapeHtml(it.nombre)}</strong></td>
            <td>${escapeHtml(it.telefono)}</td>
            <td>${estado}</td>
            <td class="text-slate-600 max-w-xs">${escapeHtml(prev)}</td>
            <td>${btn}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

async function cargarExcel() {
  const input = document.getElementById('wa-excel');
  const file = input?.files?.[0];
  if (!file) { toast('Seleccione un archivo Excel o CSV', 'info'); return; }

  const fd = new FormData();
  fd.append('archivo', file);
  document.getElementById('wa-estado').textContent = 'Leyendo Excel…';

  const res = await fetch('/api/envios-whatsapp/subir-excel', { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al leer Excel');

  contactos = data.contactos || [];
  itemsEnvio = [];
  document.getElementById('wa-resumen-contactos').innerHTML =
    `✅ <strong>${data.total}</strong> contacto(s) extraído(s) · Columnas: ${escapeHtml((data.columnas_detectadas || []).join(', '))}`;

  const adv = document.getElementById('wa-advertencias');
  if (data.advertencias?.length) {
    adv.classList.remove('hidden');
    adv.innerHTML = '⚠️ ' + data.advertencias.map(escapeHtml).join('<br>');
  } else {
    adv.classList.add('hidden');
  }

  document.getElementById('wa-estado').textContent = `${data.total} contactos`;
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`${data.total} contactos cargados del Excel`, 'ok');
}

async function generarMensajes() {
  if (!contactos.length) return;
  const res = await fetch('/api/envios-whatsapp/generar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadBase()),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al generar');

  itemsEnvio = (data.items || []).map(it => ({ ...it, _enviado: false, _error_envio: null }));
  document.getElementById('wa-estado').textContent = `${data.validos} mensajes listos`;
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`✨ ${data.validos} avisos de entrega generados`, 'ok');
}

async function exportarExcel() {
  const res = await fetch('/api/envios-whatsapp/exportar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadBase()),
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
  toast('Excel exportado con enlaces wa.me', 'ok');
}

function abrirModalEnvio() {
  const pendientes = itemsEnvio.filter(i => i.valido && !i._enviado);
  if (!pendientes.length) {
    toast('No hay contactos pendientes de envío', 'info');
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
  const btnEnviado = document.getElementById('modal-enviado');
  const titulo = document.getElementById('modal-titulo');

  if (esBusiness) {
    titulo.textContent = '📱 Envío por WhatsApp Business';
    linkWa.classList.add('hidden');
    btnBusiness.classList.remove('hidden');
    btnEnviado.textContent = '⏭️ Siguiente (ya enviado)';
  } else {
    titulo.textContent = '📤 Envío masivo wa.me';
    linkWa.classList.remove('hidden');
    btnBusiness.classList.add('hidden');
    btnEnviado.textContent = '✅ Enviado — Siguiente';
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
  const pct = Math.round((indiceCola / total) * 100);
  document.getElementById('modal-progreso').textContent = `Contacto ${indiceCola + 1} de ${total}`;
  document.getElementById('modal-barra').style.width = `${pct}%`;
  document.getElementById('modal-nombre').textContent = it.nombre;
  document.getElementById('modal-telefono').textContent = it.telefono;
  document.getElementById('modal-preview').textContent = it.mensaje;

  const link = document.getElementById('modal-abrir-wa');
  link.href = it.wa_link;

  const esBusiness = modoEnvio() === 'business' && businessApiActiva;
  if (!esBusiness) {
    window.open(it.wa_link, '_blank', 'noopener');
    if (document.getElementById('wa-auto-siguiente')?.checked) {
      clearTimeout(autoTimer);
      autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 5000);
    }
  } else if (document.getElementById('wa-auto-siguiente')?.checked && !enviandoBusiness) {
    enviarPorBusiness(it).then(ok => {
      if (ok) {
        autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 2000);
      }
    });
  }
}

async function enviarPorBusiness(it) {
  if (enviandoBusiness) return false;
  enviandoBusiness = true;
  const btn = document.getElementById('modal-enviar-business');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Enviando…';
  }

  try {
    const res = await fetch('/api/envios-whatsapp/enviar-business', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item: {
          indice: it.indice,
          telefono_limpio: it.telefono_limpio,
          mensaje: it.mensaje,
        },
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al enviar');

    const global = itemsEnvio.find(x => x.indice === it.indice);
    if (data.ok) {
      if (global) {
        global._enviado = true;
        global._error_envio = null;
      }
      toast(`✅ Enviado a ${it.nombre}`, 'ok');
      actualizarKpis();
      renderTabla();
      return true;
    }

    if (global) global._error_envio = data.error || 'Error API';
    toast(data.error || 'No se pudo enviar', 'error');
    renderTabla();
    return false;
  } catch (e) {
    toast(e.message, 'error');
    return false;
  } finally {
    enviandoBusiness = false;
    if (btn) {
      btn.disabled = false;
      btn.textContent = '📱 Enviar por Business API';
    }
  }
}

function marcarEnviadoYSiguiente() {
  clearTimeout(autoTimer);
  const it = colaEnvio[indiceCola];
  if (it) {
    const global = itemsEnvio.find(x => x.indice === it.indice);
    if (global) global._enviado = true;
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

document.getElementById('btn-cargar-excel')?.addEventListener('click', () =>
  cargarExcel().catch(e => toast(e.message, 'error')));
document.getElementById('btn-generar')?.addEventListener('click', () =>
  generarMensajes().catch(e => toast(e.message, 'error')));
document.getElementById('btn-exportar')?.addEventListener('click', () =>
  exportarExcel().catch(e => toast(e.message, 'error')));
document.getElementById('btn-enviar-masivo')?.addEventListener('click', abrirModalEnvio);
document.getElementById('btn-plantilla-ejemplo')?.addEventListener('click', () => {
  document.getElementById('wa-plantilla').value = PLANTILLA_EJ;
});
document.getElementById('modal-enviado')?.addEventListener('click', marcarEnviadoYSiguiente);
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