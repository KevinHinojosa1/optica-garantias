/**
 * Envíos masivos WhatsApp — plantilla + Excel + cola wa.me
 */

let contactos = [];
let itemsEnvio = [];
let colaEnvio = [];
let indiceCola = 0;
let autoTimer = null;

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

function payloadBase() {
  return {
    plantilla: document.getElementById('wa-plantilla').value.trim(),
    asesor: document.getElementById('wa-asesor').value.trim() || window.DEFAULT_ASESOR || '',
    incluir_pie: document.getElementById('wa-incluir-pie').checked,
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

function renderTabla() {
  const cont = document.getElementById('wa-tabla');
  if (!itemsEnvio.length) {
    cont.className = 'wa-tabla-wrap text-sm text-slate-500 py-8 text-center';
    cont.innerHTML = contactos.length
      ? `${contactos.length} contacto(s) listos — pulse <strong>Generar mensajes personalizados</strong>.`
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
  toast(`${data.total} números cargados del Excel`, 'ok');
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

  itemsEnvio = (data.items || []).map(it => ({ ...it, _enviado: false }));
  document.getElementById('wa-estado').textContent = `${data.validos} mensajes listos`;
  actualizarBotones();
  actualizarKpis();
  renderTabla();
  toast(`✨ ${data.validos} mensajes personalizados generados`, 'ok');
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
  a.download = `envios_whatsapp_${Date.now()}.xlsx`;
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
}

function mostrarContactoCola() {
  if (indiceCola >= colaEnvio.length) {
    toast('🎉 Envío masivo completado', 'ok');
    cerrarModalEnvio();
    return;
  }
  const it = colaEnvio[indiceCola];
  const total = colaEnvio.length;
  const pct = Math.round(((indiceCola) / total) * 100);
  document.getElementById('modal-progreso').textContent = `Contacto ${indiceCola + 1} de ${total}`;
  document.getElementById('modal-barra').style.width = `${pct}%`;
  document.getElementById('modal-nombre').textContent = it.nombre;
  document.getElementById('modal-telefono').textContent = it.telefono;
  document.getElementById('modal-preview').textContent = it.mensaje;
  const link = document.getElementById('modal-abrir-wa');
  link.href = it.wa_link;
  window.open(it.wa_link, '_blank', 'noopener');

  if (document.getElementById('wa-auto-siguiente').checked) {
    clearTimeout(autoTimer);
    autoTimer = setTimeout(() => marcarEnviadoYSiguiente(), 5000);
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

actualizarBotones();
actualizarKpis();