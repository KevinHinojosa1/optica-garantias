const TIENDAS = window.TIENDAS_IVR || [];
const grid = document.getElementById('ivr-grid');
const historialDiv = document.getElementById('ivr-historial');
const contadorDiv = document.getElementById('ivr-contador');
const inputVerificador = document.getElementById('verificador-ivr');
let ciudadFiltro = '';
let diaFiltro = window.DIA_HOY ? 'hoy' : '1';
let estados = {};

const BTN_FILTRO = 'shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-medium glass-btn whitespace-nowrap text-slate-600';
const BTN_FILTRO_ACTIVE = BTN_FILTRO + ' glass-btn-active';

const SUGERENCIAS_IVR = [
  {
    texto: 'Funciona bien IVR',
    funciona: true,
    base: 'bg-emerald-50 border-emerald-200 text-emerald-800 hover:bg-emerald-100',
    activa: 'bg-emerald-600 border-emerald-600 text-white ring-2 ring-emerald-300',
  },
  {
    texto: 'Funciona bien, no contesta',
    funciona: true,
    base: 'bg-amber-50 border-amber-200 text-amber-800 hover:bg-amber-100',
    activa: 'bg-amber-500 border-amber-500 text-white ring-2 ring-amber-300',
  },
  {
    texto: 'No funciona IVR',
    funciona: false,
    base: 'bg-red-50 border-red-200 text-red-800 hover:bg-red-100',
    activa: 'bg-red-600 border-red-600 text-white ring-2 ring-red-300',
  },
  {
    texto: 'Funciona IVR pero se cuelga la llamada',
    funciona: false,
    base: 'bg-orange-50 border-orange-200 text-orange-800 hover:bg-orange-100',
    activa: 'bg-orange-500 border-orange-600 text-white ring-2 ring-orange-300',
  },
];

function scriptLlamada(nombre) {
  const quien = nombre?.trim() || '…';
  return `Hola compañero, mi nombre es ${quien} y es una llamada de prueba del IVR, listo.`;
}

function nombreVerificador() {
  return inputVerificador?.value.trim() || '';
}

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function normalizarTexto(t) {
  return (t || '').trim().toLowerCase();
}

function etiquetaEstado(registro) {
  if (registro.comentario) return registro.comentario;
  if (registro.funciona === true) return 'IVR vale (1)';
  if (registro.funciona === false) return 'IVR no vale (0)';
  return '—';
}

function claseSugerencia(comentario, sugerencia) {
  return normalizarTexto(comentario) === normalizarTexto(sugerencia.texto)
    ? sugerencia.activa
    : sugerencia.base;
}

function claseValBoton(funciona, esperado) {
  if (funciona === esperado) {
    return esperado
      ? 'glass-btn glass-val-ok glass-val-ok-active border'
      : 'glass-btn glass-val-no glass-val-no-active border';
  }
  return esperado
    ? 'glass-btn glass-val-ok border hover:opacity-90'
    : 'glass-btn glass-val-no border hover:opacity-90';
}

function htmlSugerencias(tiendaId, comentarioActual) {
  return SUGERENCIAS_IVR.map(s => {
    const textoJs = s.texto.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    return `
    <button type="button"
      onclick="aplicarSugerencia('${tiendaId}', '${textoJs}', ${s.funciona})"
      class="w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition ${claseSugerencia(comentarioActual, s)}">
      ${escapeHtml(s.texto)}
    </button>`;
  }).join('');
}

function htmlSugerenciasEditar(comentarioActual) {
  return SUGERENCIAS_IVR.map((s, i) => `
    <button type="button" data-sug-idx="${i}"
      class="sug-editar w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition ${claseSugerencia(comentarioActual, s)}">
      ${escapeHtml(s.texto)}
    </button>
  `).join('');
}

function setFiltroDiaActivo(btn) {
  document.querySelectorAll('.filtro-dia').forEach(b => {
    b.className = 'filtro-dia ' + BTN_FILTRO;
  });
  btn.className = 'filtro-dia ' + BTN_FILTRO_ACTIVE;
  diaFiltro = btn.dataset.dia;
  renderGrid();
}

document.querySelectorAll('.filtro-dia').forEach(btn => {
  btn.addEventListener('click', () => setFiltroDiaActivo(btn));
});

document.querySelectorAll('.filtro-ciudad').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filtro-ciudad').forEach(b => {
      b.className = 'filtro-ciudad ' + BTN_FILTRO;
    });
    btn.className = 'filtro-ciudad ' + BTN_FILTRO_ACTIVE;
    ciudadFiltro = btn.dataset.ciudad;
    renderGrid();
  });
});

async function cargarEstado() {
  const res = await fetch(`/api/ivr/estado?semana=${encodeURIComponent(window.SEMANA_ACTUAL)}`);
  const data = await res.json();
  if (res.ok) {
    estados = {};
    data.forEach(e => { estados[e.tienda_id] = e; });
  }
  renderGrid();
}

function filtrarTiendas() {
  let lista = TIENDAS;
  if (diaFiltro === 'hoy' && window.DIA_HOY) {
    lista = lista.filter(t => t.dia_ivr === window.DIA_HOY);
  } else if (diaFiltro !== 'todas' && diaFiltro !== '') {
    lista = lista.filter(t => t.dia_ivr === Number(diaFiltro));
  }
  if (ciudadFiltro) {
    lista = lista.filter(t => t.ciudad === ciudadFiltro);
  }
  return lista;
}

function cardTienda(tienda) {
  const e = estados[tienda.id] || {};
  const funciona = e.funciona;
  const verificado = e.verificado_at
    ? new Date(e.verificado_at).toLocaleString('es-EC')
    : 'Sin verificar esta semana';
  const comentario = e.comentario || '';
  const auditoria = e.comentario_auditoria || '';
  const esSugerencia = SUGERENCIAS_IVR.some(s => normalizarTexto(s.texto) === normalizarTexto(comentario));
  const gestionExtra = comentario && !esSugerencia ? comentario : '';

  return `
    <div class="glass-card p-4 sm:p-5 flex flex-col gap-3" id="card-${tienda.id}">
      <div>
        <div class="flex flex-wrap items-center gap-2 mb-1.5">
          <span class="glass-pill text-xs font-medium px-2 py-0.5 rounded-full text-slate-600">Día ${tienda.dia_ivr}</span>
          <span class="text-xs font-medium text-slate-500 uppercase tracking-wide">${escapeHtml(tienda.ciudad)}</span>
          ${funciona === true ? '<span class="glass-pill text-xs font-semibold px-2 py-0.5 rounded-full text-emerald-700">Vale: 1</span>' : ''}
          ${funciona === false ? '<span class="glass-pill text-xs font-semibold px-2 py-0.5 rounded-full text-red-600">Vale: 0</span>' : ''}
        </div>
        <h4 class="font-semibold text-slate-800 leading-snug">${escapeHtml(tienda.nombre)}</h4>
        <p class="text-xs text-slate-400 mt-1">${verificado}</p>
        ${comentario && esSugerencia ? `<p class="text-xs text-slate-600 mt-2 glass-card-inner px-2.5 py-1.5">${escapeHtml(comentario)}</p>` : ''}
      </div>
      <div class="glass-card-inner p-3">
        <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Script</p>
        <p class="script-llamada text-sm text-slate-600 leading-relaxed italic">${escapeHtml(scriptLlamada(nombreVerificador()))}</p>
      </div>
      <div class="flex items-center justify-between gap-3 glass-card-inner p-3">
        <div>
          <p class="text-xs font-medium text-slate-600 uppercase tracking-wide">IVR Vale</p>
          <p class="text-xs text-slate-400">✓ → 1 · ✗ → 0</p>
        </div>
        <div class="flex gap-2 shrink-0">
          <button type="button" onclick="marcarValIvr('${tienda.id}', true)"
            class="w-10 h-10 rounded-xl font-semibold text-base transition ${claseValBoton(funciona, true)}" title="Guardar 1">✓</button>
          <button type="button" onclick="marcarValIvr('${tienda.id}', false)"
            class="w-10 h-10 rounded-xl font-semibold text-base transition ${claseValBoton(funciona, false)}" title="Guardar 0">✗</button>
        </div>
      </div>
      <div>
        <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Sugerencias</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          ${htmlSugerencias(tienda.id, comentario)}
        </div>
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Detalle gestión</label>
        <textarea id="gestion-${tienda.id}" rows="2" placeholder="Nota operativa..."
          class="glass-textarea w-full px-3 py-2 text-sm">${escapeHtml(gestionExtra)}</textarea>
      </div>
      <div class="glass-card-inner p-3">
        <label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Auditoría</label>
        <p class="text-xs text-slate-500 mb-2">Comentario de control de calidad.</p>
        <textarea id="auditoria-${tienda.id}" rows="3" placeholder="Observaciones del auditor..."
          class="glass-textarea w-full px-3 py-2 text-sm">${escapeHtml(auditoria)}</textarea>
      </div>
      <p id="status-${tienda.id}" class="text-xs text-slate-400 min-h-[1rem]"></p>
    </div>
  `;
}

function actualizarContador(cantidad) {
  if (!contadorDiv) return;
  let diaLabel = 'todas las tiendas';
  if (diaFiltro === 'hoy' && window.DIA_HOY) diaLabel = `Día ${window.DIA_HOY} (hoy)`;
  else if (diaFiltro !== 'todas') diaLabel = `Día ${diaFiltro}`;
  const ciudadLabel = ciudadFiltro ? ` · ${ciudadFiltro}` : '';
  contadorDiv.textContent = `Mostrando ${cantidad} tienda(s) — ${diaLabel}${ciudadLabel}`;
}

function renderGrid() {
  const lista = filtrarTiendas();
  actualizarContador(lista.length);
  if (!lista.length) {
    grid.innerHTML = '<p class="col-span-full text-center text-slate-400 py-8">No hay tiendas con este filtro</p>';
    return;
  }
  grid.innerHTML = lista.map(cardTienda).join('');
}

function payloadDesdeCard(tiendaId, funciona, comentarioForzado = null) {
  const gestion = document.getElementById(`gestion-${tiendaId}`)?.value.trim() || '';
  const auditoria = document.getElementById(`auditoria-${tiendaId}`)?.value.trim() || '';
  let comentario = '';
  if (comentarioForzado) {
    comentario = gestion ? `${comentarioForzado} — ${gestion}` : comentarioForzado;
  } else {
    comentario = gestion;
  }
  return {
    tienda_id: tiendaId,
    funciona,
    comentario,
    comentario_auditoria: auditoria,
    verificado_por: document.getElementById('verificador-ivr')?.value.trim() || 'Equipo de Tienda',
  };
}

async function marcarIvr(tiendaId, funciona, comentarioForzado = null) {
  const status = document.getElementById(`status-${tiendaId}`);
  status.textContent = 'Guardando...';
  status.className = 'text-xs text-slate-500';

  try {
    const res = await fetch('/api/ivr/registrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payloadDesdeCard(tiendaId, funciona, comentarioForzado)),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    const hora = new Date(data.created_at).toLocaleString('es-EC');
    let msg = `✅ Guardado ${hora} · IVR Vale: ${data.ivr_vale}`;
    if (data.google_sheets_ok) msg += ' · Google Sheets ✓';
    else if (data.google_sheets_mensaje) msg += ` · ${data.google_sheets_mensaje}`;
    status.textContent = msg;
    status.className = 'text-xs text-emerald-600 font-medium';

    await cargarEstado();
    cargarHistorialIvr();
  } catch (err) {
    status.textContent = '❌ ' + err.message;
    status.className = 'text-xs text-red-600';
  }
}

async function marcarValIvr(tiendaId, funciona) {
  await marcarIvr(tiendaId, funciona, null);
}
async function aplicarSugerencia(tiendaId, texto, funciona) {
  await marcarIvr(tiendaId, funciona, texto);
}
window.aplicarSugerencia = aplicarSugerencia;
window.marcarValIvr = marcarValIvr;
window.marcarIvr = marcarIvr;

let editarFunciona = true;
let editarSugerenciaTexto = '';
let historialRegistros = {};

const modalEditar = document.getElementById('modal-editar-ivr');
const editarStatus = document.getElementById('editar-ivr-status');
const editarSugerencias = document.getElementById('editar-sugerencias');

function actualizarBotonesValEditar() {
  const btnSi = document.getElementById('editar-val-si');
  const btnNo = document.getElementById('editar-val-no');
  if (!btnSi || !btnNo) return;
  btnSi.className = `flex-1 py-2.5 rounded-xl font-semibold text-lg transition ${claseValBoton(editarFunciona, true)}`;
  btnNo.className = `flex-1 py-2.5 rounded-xl font-semibold text-lg transition ${claseValBoton(editarFunciona, false)}`;
}

function seleccionarSugerenciaEditar(sugerencia) {
  editarFunciona = sugerencia.funciona;
  editarSugerenciaTexto = sugerencia.texto;
  editarSugerencias.innerHTML = htmlSugerenciasEditar(sugerencia.texto);
  editarSugerencias.querySelectorAll('.sug-editar').forEach((btn, idx) => {
    btn.addEventListener('click', () => seleccionarSugerenciaEditar(SUGERENCIAS_IVR[idx]));
  });
  actualizarBotonesValEditar();
}

function abrirModalEditar(registro) {
  document.getElementById('editar-ivr-id').value = registro.id;
  document.getElementById('modal-ivr-tienda').textContent =
    `${registro.tienda_nombre} (${registro.ciudad}) · ${new Date(registro.created_at).toLocaleString('es-EC')}`;
  document.getElementById('editar-verificador').value =
    registro.verificado_por || document.getElementById('verificador-ivr')?.value.trim() || '';
  document.getElementById('editar-auditoria').value = registro.comentario_auditoria || '';

  const comentario = registro.comentario || '';
  const sugerencia = SUGERENCIAS_IVR.find(s => normalizarTexto(s.texto) === normalizarTexto(comentario));
  editarFunciona = registro.funciona;
  if (sugerencia) {
    seleccionarSugerenciaEditar(sugerencia);
    document.getElementById('editar-comentario').value = '';
  } else {
    editarSugerenciaTexto = '';
    editarSugerencias.innerHTML = htmlSugerenciasEditar('');
    editarSugerencias.querySelectorAll('.sug-editar').forEach((btn, idx) => {
      btn.addEventListener('click', () => seleccionarSugerenciaEditar(SUGERENCIAS_IVR[idx]));
    });
    document.getElementById('editar-comentario').value = comentario;
    actualizarBotonesValEditar();
  }

  editarStatus.textContent = '';
  modalEditar.classList.remove('hidden');
}

function cerrarModalEditar() {
  modalEditar.classList.add('hidden');
}

async function guardarEdicionIvr() {
  const id = document.getElementById('editar-ivr-id').value;
  const extra = document.getElementById('editar-comentario').value.trim();
  const auditoria = document.getElementById('editar-auditoria').value.trim();
  let comentario = '';
  if (editarSugerenciaTexto) {
    comentario = extra ? `${editarSugerenciaTexto} — ${extra}` : editarSugerenciaTexto;
  } else {
    comentario = extra;
  }
  editarStatus.textContent = 'Guardando...';
  editarStatus.className = 'text-sm text-slate-500';
  try {
    const res = await fetch(`/api/ivr/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        funciona: editarFunciona,
        comentario,
        comentario_auditoria: auditoria,
        verificado_por: document.getElementById('editar-verificador').value.trim() || 'Equipo de Tienda',
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    cerrarModalEditar();
    await cargarEstado();
    cargarHistorialIvr();
  } catch (err) {
    editarStatus.textContent = '❌ ' + err.message;
    editarStatus.className = 'text-sm text-red-600';
  }
}

async function eliminarRegistroIvr(id, tiendaNombre) {
  if (!confirm(`¿Eliminar el registro IVR de ${tiendaNombre}?`)) return;
  try {
    const res = await fetch(`/api/ivr/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    await cargarEstado();
    cargarHistorialIvr();
  } catch (err) {
    alert('Error al eliminar: ' + err.message);
  }
}

async function cargarHistorialIvr() {
  try {
    const res = await fetch('/api/ivr/historial?limit=30');
    const data = await res.json();
    historialRegistros = {};
    data.forEach(r => { historialRegistros[r.id] = r; });
    if (!data.length) {
      historialDiv.innerHTML = '<p class="text-slate-400">Sin registros aún</p>';
      return;
    }
    historialDiv.innerHTML = `
      <div class="overflow-x-auto overflow-touch">
        <table class="w-full text-xs sm:text-sm min-w-[800px]">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="text-left px-3 py-2">Fecha/Hora</th>
              <th class="text-left px-3 py-2">Tienda</th>
              <th class="text-center px-3 py-2">IVR Vale</th>
              <th class="text-left px-3 py-2">Detalle</th>
              <th class="text-left px-3 py-2">Auditoría</th>
              <th class="text-left px-3 py-2">Verificador</th>
              <th class="text-right px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(r => `
              <tr class="border-t hover:bg-slate-50/50">
                <td class="px-3 py-2 whitespace-nowrap">${new Date(r.created_at).toLocaleString('es-EC')}</td>
                <td class="px-3 py-2">${escapeHtml(r.tienda_nombre)} <span class="text-slate-400 text-xs">(${escapeHtml(r.ciudad)})</span></td>
                <td class="px-3 py-2 text-center font-bold ${r.ivr_vale === 1 ? 'text-emerald-600' : 'text-red-600'}">${r.ivr_vale}</td>
                <td class="px-3 py-2 font-medium text-slate-700">${escapeHtml(etiquetaEstado(r))}</td>
                <td class="px-3 py-2 text-slate-500 max-w-xs truncate" title="${escapeHtml(r.comentario_auditoria || '')}">${escapeHtml(r.comentario_auditoria || '—')}</td>
                <td class="px-3 py-2">${escapeHtml(r.verificado_por)}</td>
                <td class="px-3 py-2 text-right whitespace-nowrap">
                  <button type="button" data-id="${r.id}"
                    class="editar-ivr px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-optica-50 text-optica-700 hover:bg-optica-100 border border-optica-200 transition">
                    ✏️ Editar
                  </button>
                  <button type="button" data-id="${r.id}" data-tienda="${escapeHtml(r.tienda_nombre)}"
                    class="eliminar-ivr ml-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition">
                    🗑️ Eliminar
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    historialDiv.querySelectorAll('.editar-ivr').forEach(btn => {
      btn.addEventListener('click', () => {
        const reg = historialRegistros[btn.dataset.id];
        if (reg) abrirModalEditar(reg);
      });
    });
    historialDiv.querySelectorAll('.eliminar-ivr').forEach(btn => {
      btn.addEventListener('click', () => {
        eliminarRegistroIvr(btn.dataset.id, btn.dataset.tienda);
      });
    });
  } catch {
    historialDiv.innerHTML = '<p class="text-red-500">Error al cargar historial</p>';
  }
}

document.getElementById('editar-val-si')?.addEventListener('click', () => {
  editarFunciona = true;
  actualizarBotonesValEditar();
});
document.getElementById('editar-val-no')?.addEventListener('click', () => {
  editarFunciona = false;
  actualizarBotonesValEditar();
});
document.getElementById('btn-guardar-editar-ivr')?.addEventListener('click', guardarEdicionIvr);
document.getElementById('btn-cancelar-editar-ivr')?.addEventListener('click', cerrarModalEditar);
document.getElementById('btn-cerrar-modal-ivr')?.addEventListener('click', cerrarModalEditar);
modalEditar?.addEventListener('click', e => {
  if (e.target === modalEditar) cerrarModalEditar();
});

inputVerificador?.addEventListener('input', () => {
  document.querySelectorAll('.script-llamada').forEach(el => {
    el.textContent = scriptLlamada(nombreVerificador());
  });
});

cargarEstado();
cargarHistorialIvr();