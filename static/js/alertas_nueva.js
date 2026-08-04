/**
 * alertas_nueva.js
 * Maneja:
 *  - Navegación entre tabs (Matriz / Nueva Alerta / Reporte IA)
 *  - Formulario de ingreso de nueva alerta
 *  - Generación y renderizado del Reporte IA con Claude
 */

/* ─── Tabs principales ─── */
document.querySelectorAll('.main-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.main-tab').forEach(t => {
      t.classList.remove('active', 'border-optica-600', 'text-optica-700');
      t.classList.add('text-slate-500', 'border-transparent');
    });
    tab.classList.add('active', 'border-optica-600', 'text-optica-700');
    tab.classList.remove('text-slate-500', 'border-transparent');

    const panelId = tab.dataset.panel;
    ['panel-matriz', 'panel-nueva-alerta', 'panel-reporte-ia'].forEach(id => {
      document.getElementById(id)?.classList.toggle('hidden', id !== panelId);
    });
  });
});

/* ─── Helpers ─── */
function escHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function toastNa(msg, tipo = 'info') {
  const el = document.getElementById('toast-alertas');
  if (!el) return;
  el.textContent = msg;
  el.className = `fixed bottom-4 right-4 z-50 glass-card px-4 py-3 text-sm font-medium shadow-lg toast-${tipo}`;
  el.classList.remove('hidden');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), 5000);
}

function switchToReporte() {
  const tab = document.querySelector('.main-tab[data-panel="panel-reporte-ia"]');
  if (tab) tab.click();
}

/* ─── Leer formulario nueva alerta ─── */
function leerFormulario() {
  const v = id => document.getElementById(id)?.value?.trim() || '';
  return {
    local: v('na-local'),
    area: v('na-area'),
    fecha_alerta: v('na-fecha'),
    canal: v('na-canal') || 'Manual',
    cliente: v('na-cliente'),
    contacto: v('na-contacto'),
    optometra: v('na-optometra'),
    asesor: v('na-asesor'),
    calificacion: v('na-calificacion'),
    clasificacion: v('na-clasificacion'),
    estado_gestion: v('na-estado') || 'Sin gestión',
    llamada_cliente: v('na-llamada') || 'Pendiente',
    comentario: v('na-comentario'),
    observacion_gestion: v('na-observacion'),
    solucion: v('na-solucion'),
    contexto_extra: v('na-contexto-ia'),
  };
}

function limpiarFormulario() {
  ['na-local','na-area','na-fecha','na-canal','na-cliente','na-contacto',
   'na-optometra','na-asesor','na-calificacion','na-clasificacion',
   'na-estado','na-llamada','na-comentario','na-observacion','na-solucion',
   'na-contexto-ia'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  const est = document.getElementById('na-estado');
  if (est) {
    const opt = [...est.options].find(o => o.value === 'Sin gestión');
    if (opt) est.value = 'Sin gestión';
  }
  const ll = document.getElementById('na-llamada');
  if (ll) {
    const opt = [...ll.options].find(o => o.value === 'Pendiente');
    if (opt) ll.value = 'Pendiente';
  }
  const naEst = document.getElementById('na-estado-msg');
  if (naEst) { naEst.classList.add('hidden'); naEst.textContent = ''; }
}

function mostrarEstadoNa(msg, tipo) {
  let el = document.getElementById('na-estado-msg');
  if (!el) {
    el = document.createElement('div');
    el.id = 'na-estado-msg';
    document.getElementById('na-estado')?.parentElement?.appendChild(el);
  }
  const colores = { ok: 'bg-emerald-50 text-emerald-800 border-emerald-200',
                    error: 'bg-red-50 text-red-800 border-red-200',
                    info: 'bg-sky-50 text-sky-800 border-sky-200' };
  el.className = `mt-4 p-3 rounded-xl text-sm font-medium border ${colores[tipo] || colores.info}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

/* ─── Guardar alerta ─── */
async function guardarAlerta(conReporte = false) {
  const datos = leerFormulario();
  if (!datos.local) { toastNa('Selecciona el Local / Tienda', 'error'); return null; }
  if (!datos.comentario) { toastNa('El comentario es obligatorio', 'error'); return null; }

  const btnId = conReporte ? 'btn-na-guardar-reporte' : 'btn-na-guardar';
  const btn = document.getElementById(btnId);
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Guardando...'; }

  try {
    const res = await fetch('/api/alertas/ingresar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al guardar');
    toastNa(`✅ Alerta #${data.n} guardada correctamente`, 'ok');
    mostrarEstadoNa(`✅ Alerta #${data.n} ingresada al sistema (ID interno: ${data.id}).`, 'ok');
    return data;
  } catch (e) {
    toastNa(e.message, 'error');
    mostrarEstadoNa('❌ ' + e.message, 'error');
    return null;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = conReporte ? '🤖 Guardar + Reporte IA' : '💾 Guardar alerta'; }
  }
}

document.getElementById('btn-na-guardar')?.addEventListener('click', async () => {
  await guardarAlerta(false);
});

document.getElementById('btn-na-guardar-reporte')?.addEventListener('click', async () => {
  const datos = leerFormulario();
  if (!datos.local) { toastNa('Selecciona el Local / Tienda', 'error'); return; }
  if (!datos.comentario) { toastNa('El comentario es obligatorio', 'error'); return; }

  const result = await guardarAlerta(false);
  if (!result) return;

  // Ahora generar el reporte IA con la fila recién creada
  await generarReporteIA(result.fila, datos.contexto_extra);
});

document.getElementById('btn-na-limpiar')?.addEventListener('click', limpiarFormulario);

/* ─── Reporte IA ─── */
let filaReporte = null;

async function generarReporteIA(fila, contextoExtra = '') {
  filaReporte = fila;

  // Ir al panel de reporte
  switchToReporte();

  // Mostrar estado
  document.getElementById('reporte-cargando')?.classList.remove('hidden');
  document.getElementById('reporte-resultado')?.classList.add('hidden');
  document.getElementById('reporte-vacio')?.classList.add('hidden');

  // Label del caso
  const label = document.getElementById('reporte-caso-label');
  if (label) {
    const cliente = fila.cliente || fila.nombre || '—';
    const local = fila.local || '—';
    label.textContent = `Analizando: ${cliente} · ${local}`;
  }

  try {
    const res = await fetch('/api/alertas/reporte-ia', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fila, contexto_extra: contextoExtra || '' }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al generar reporte');
    if (!data.ok || !data.reporte) throw new Error(data.error || 'Claude no devolvió un reporte válido');

    renderizarReporte(data);
  } catch (e) {
    toastNa('Error: ' + e.message, 'error');
    document.getElementById('reporte-cargando')?.classList.add('hidden');
    document.getElementById('reporte-vacio')?.classList.remove('hidden');
    document.getElementById('reporte-vacio').innerHTML = `
      <div class="text-4xl mb-3">⚠️</div>
      <p class="font-medium text-red-700">Error al generar reporte</p>
      <p class="text-sm mt-1 text-red-500">${escHtml(e.message)}</p>`;
  }
}

function renderizarReporte(data) {
  const r = data.reporte;
  const caso = data.caso || filaReporte || {};

  document.getElementById('reporte-cargando')?.classList.add('hidden');
  document.getElementById('reporte-vacio')?.classList.add('hidden');
  document.getElementById('reporte-resultado')?.classList.remove('hidden');

  // Título
  const titulo = document.getElementById('rpt-titulo');
  if (titulo) titulo.textContent = `${caso.cliente || '—'} · ${caso.local || '—'}`;

  // Badges
  const badges = document.getElementById('rpt-badges');
  if (badges) {
    const nivel = (r.nivel_riesgo || 'bajo').toLowerCase();
    const riesgoCls = { alto: 'riesgo-alto', medio: 'riesgo-medio', bajo: 'riesgo-bajo' }[nivel] || 'riesgo-bajo';
    const iconRiesgo = { alto: '🔴', medio: '🟡', bajo: '🟢' }[nivel] || '🟢';
    const escal = r.requiere_escalamiento ? '🚨 Requiere escalamiento' : '✅ Sin escalamiento';
    const escalCls = r.requiere_escalamiento ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800';
    badges.innerHTML = `
      <span class="riesgo-badge ${riesgoCls}">${iconRiesgo} Riesgo ${nivel}</span>
      <span class="riesgo-badge ${escalCls} border-0">${escal}</span>
      ${caso.clasificacion ? `<span class="riesgo-badge bg-slate-100 text-slate-700">🏷️ ${escHtml(caso.clasificacion)}</span>` : ''}`;
  }

  // Resumen
  const resumen = document.getElementById('rpt-resumen');
  if (resumen) resumen.textContent = r.resumen_ejecutivo || '—';

  // Hallazgos
  const hallazgos = document.getElementById('rpt-hallazgos');
  if (hallazgos) {
    if (!r.hallazgos?.length) {
      hallazgos.innerHTML = '<p class="text-sm text-slate-400">Sin hallazgos registrados.</p>';
    } else {
      hallazgos.innerHTML = r.hallazgos.map(h => {
        const sev = (h.severidad || 'baja').toLowerCase();
        const sevCls = { alta: 'hallazgo-alta', media: 'hallazgo-media', baja: 'hallazgo-baja' }[sev] || 'hallazgo-baja';
        const sevIco = { alta: '🔴', media: '🟡', baja: '🟢' }[sev] || '🟢';
        return `<div class="hallazgo-card ${sevCls}">
          <p class="font-semibold text-sm text-slate-800">${sevIco} ${escHtml(h.titulo || '—')}</p>
          <p class="text-sm text-slate-600 mt-1">${escHtml(h.descripcion || '')}</p>
        </div>`;
      }).join('');
    }
  }

  // Acciones
  const acciones = document.getElementById('rpt-acciones');
  if (acciones) {
    if (!r.acciones_recomendadas?.length) {
      acciones.innerHTML = '<p class="text-sm text-slate-400">Sin acciones recomendadas.</p>';
    } else {
      acciones.innerHTML = r.acciones_recomendadas.map(a => {
        const plazo = (a.plazo || 'esta_semana').toLowerCase();
        const plazoCls = { inmediato: 'accion-inmediato', '24h': 'accion-24h', esta_semana: 'accion-semana' }[plazo] || 'accion-semana';
        const plazoLabel = { inmediato: 'Inmediato', '24h': '24 horas', esta_semana: 'Esta semana' }[plazo] || plazo;
        const respIco = { local: '🏪', optometra: '👓', asesor: '👤', call_center: '📞' }[a.responsable] || '▸';
        return `<div class="accion-card">
          <span class="accion-badge ${plazoCls}">${plazoLabel}</span>
          <div class="flex-1">
            <p class="text-xs font-bold text-slate-500 uppercase mb-0.5">${respIco} ${escHtml(a.responsable || '—')}</p>
            <p class="text-sm text-slate-700">${escHtml(a.accion || '')}</p>
          </div>
        </div>`;
      }).join('');
    }
  }

  // Análisis por actor
  document.getElementById('rpt-local').textContent = r.analisis_local || '—';
  document.getElementById('rpt-optometra').textContent = r.analisis_optometra || '—';
  document.getElementById('rpt-asesor').textContent = r.analisis_asesor || '—';

  // Nota CXD
  document.getElementById('rpt-nota-cxd').textContent = r.nota_cxd || '—';

  // Meta
  const meta = document.getElementById('rpt-meta');
  if (meta) meta.textContent = `Generado por Claude · ${data.generado_por || ''} · ${new Date().toLocaleString('es-EC')}`;
}

/* Botón "Generar reporte" del panel vacío */
document.getElementById('btn-reporte-generar')?.addEventListener('click', () => {
  if (filaReporte) {
    generarReporteIA(filaReporte, '');
  } else if (typeof filaSeleccionada !== 'undefined' && filaSeleccionada) {
    generarReporteIA(filaSeleccionada, document.getElementById('ia-contexto-extra')?.value || '');
  } else {
    toastNa('Selecciona primero un caso en la Matriz', 'info');
  }
});

/* Botón "Reporte IA del caso" en Más acciones (se activa en alertas.js con filaSeleccionada) */
document.getElementById('btn-reporte-fila')?.addEventListener('click', () => {
  if (typeof filaSeleccionada !== 'undefined' && filaSeleccionada) {
    generarReporteIA(filaSeleccionada, document.getElementById('ia-contexto-extra')?.value || '');
  } else {
    toastNa('Selecciona primero un caso en la tabla', 'info');
  }
  document.getElementById('menu-mas-acciones')?.classList.add('hidden');
});

/* Botón "Reporte IA" dentro del modal de edición */
document.getElementById('modal-reporte-ia')?.addEventListener('click', () => {
  const fila = typeof filaSeleccionada !== 'undefined' ? filaSeleccionada : null;
  if (fila) {
    document.getElementById('modal-editar')?.classList.add('hidden');
    generarReporteIA(fila, '');
  } else {
    toastNa('Selecciona un caso antes de generar el reporte', 'info');
  }
});

/* Exponer función globalmente para que alertas.js la pueda usar */
window.generarReporteIA = generarReporteIA;
