const TIENDAS = window.TIENDAS_IVR || [];
const grid = document.getElementById('ivr-grid');
const historialDiv = document.getElementById('ivr-historial');
const contadorDiv = document.getElementById('ivr-contador');
const inputVerificador = document.getElementById('verificador-ivr');
let ciudadFiltro = '';
let diaFiltro = window.DIA_HOY ? 'hoy' : '1';
let estados = {};
const borradores = {};

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

function parseComentarioGuardado(comentario) {
  if (!comentario) return { sugerencia: '', gestion: '' };
  const exacta = SUGERENCIAS_IVR.find(s => normalizarTexto(s.texto) === normalizarTexto(comentario));
  if (exacta) return { sugerencia: exacta.texto, gestion: '' };
  for (const s of SUGERENCIAS_IVR) {
    const prefijo = s.texto + ' — ';
    if (comentario.startsWith(prefijo)) {
      return { sugerencia: s.texto, gestion: comentario.slice(prefijo.length) };
    }
  }
  return { sugerencia: '', gestion: comentario };
}

function getBorrador(tiendaId) {
  if (borradores[tiendaId]) return borradores[tiendaId];
  const e = estados[tiendaId] || {};
  const parsed = parseComentarioGuardado(e.comentario || '');
  borradores[tiendaId] = {
    funciona: e.funciona ?? null,
    sugerencia: parsed.sugerencia,
    gestion: parsed.gestion,
    auditoria: e.comentario_auditoria || '',
    guardado: !!(e.verificado_at),
  };
  return borradores[tiendaId];
}

function syncBorradorFromInputs(tiendaId) {
  const b = getBorrador(tiendaId);
  b.gestion = document.getElementById(`gestion-${tiendaId}`)?.value.trim() || '';
  b.auditoria = document.getElementById(`auditoria-${tiendaId}`)?.value.trim() || '';
}

function textoChecklist(b) {
  const pasos = [];
  if (b.funciona === true || b.funciona === false) {
    pasos.push(`IVR Vale: ${b.funciona ? '1' : '0'}`);
  } else {
    pasos.push('Seleccione ✓ o ✗');
  }
  if (b.sugerencia) pasos.push('Sugerencia lista');
  else pasos.push('Seleccione una sugerencia');
  return pasos.join(' · ');
}

function htmlSugerencias(tiendaId, sugerenciaActual) {
  return SUGERENCIAS_IVR.map(s => {
    const textoJs = s.texto.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    return `
    <button type="button" data-sug-btn="${tiendaId}"
      onclick="seleccionarSugerencia('${tiendaId}', '${textoJs}', ${s.funciona})"
      class="w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition ${claseSugerencia(sugerenciaActual, s)}">
      ${escapeHtml(s.texto)}
    </button>`;
  }).join('');
}

function refrescarCardUI(tiendaId) {
  const b = getBorrador(tiendaId);
  const card = document.getElementById(`card-${tiendaId}`);
  if (!card) return;

  card.querySelectorAll('[data-val-btn]').forEach(btn => {
    const ok = btn.dataset.val === '1';
    btn.className = `w-10 h-10 rounded-xl font-semibold text-base transition ${claseValBoton(b.funciona, ok)}`;
  });
  card.querySelectorAll('[data-sug-btn]').forEach((btn, idx) => {
    btn.className = `w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition ${claseSugerencia(b.sugerencia, SUGERENCIAS_IVR[idx])}`;
  });

  const checklist = document.getElementById(`checklist-${tiendaId}`);
  if (checklist) checklist.textContent = textoChecklist(b);

  const badgeVal = document.getElementById(`badge-val-${tiendaId}`);
  if (badgeVal) {
    if (b.funciona === true) {
      badgeVal.className = 'glass-pill text-xs font-semibold px-2 py-0.5 rounded-full text-emerald-700';
      badgeVal.textContent = 'Vale: 1';
      badgeVal.classList.remove('hidden');
    } else if (b.funciona === false) {
      badgeVal.className = 'glass-pill text-xs font-semibold px-2 py-0.5 rounded-full text-red-600';
      badgeVal.textContent = 'Vale: 0';
      badgeVal.classList.remove('hidden');
    } else {
      badgeVal.classList.add('hidden');
    }
  }
}

function seleccionarVal(tiendaId, funciona) {
  const b = getBorrador(tiendaId);
  b.funciona = funciona;
  refrescarCardUI(tiendaId);
}
window.seleccionarVal = seleccionarVal;

function seleccionarSugerencia(tiendaId, texto, funcionaSug) {
  const b = getBorrador(tiendaId);
  b.sugerencia = texto;
  if (b.funciona === null || b.funciona === undefined) {
    b.funciona = funcionaSug;
  }
  refrescarCardUI(tiendaId);
}
window.seleccionarSugerencia = seleccionarSugerencia;

function htmlSugerenciasEditar(comentarioActual) {
  return SUGERENCIAS_IVR.map((s, i) => `
    <button type="button" data-sug-idx="${i}"
      class="sug-editar w-full text-left px-3 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition ${claseSugerencia(comentarioActual, s)}">
      ${escapeHtml(s.texto)}
    </button>
  `).join('');
}

function preservarBorradoresVisibles() {
  Object.keys(borradores).forEach(syncBorradorFromInputs);
}

function setFiltroDiaActivo(btn) {
  preservarBorradoresVisibles();
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
    preservarBorradoresVisibles();
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
  const b = getBorrador(tienda.id);
  const verificado = e.verificado_at
    ? new Date(e.verificado_at).toLocaleString('es-EC')
    : 'Sin verificar esta semana';
  const badgeHidden = b.funciona === null || b.funciona === undefined ? 'hidden' : '';

  return `
    <div class="glass-card p-4 sm:p-5 flex flex-col gap-3" id="card-${tienda.id}">
      <div>
        <div class="flex flex-wrap items-center gap-2 mb-1.5">
          <span class="glass-pill text-xs font-medium px-2 py-0.5 rounded-full text-slate-600">Día ${tienda.dia_ivr}</span>
          <span class="text-xs font-medium text-slate-500 uppercase tracking-wide">${escapeHtml(tienda.ciudad)}</span>
          <span id="badge-val-${tienda.id}" class="glass-pill text-xs font-semibold px-2 py-0.5 rounded-full ${badgeHidden} ${b.funciona === true ? 'text-emerald-700' : b.funciona === false ? 'text-red-600' : ''}">
            ${b.funciona === true ? 'Vale: 1' : b.funciona === false ? 'Vale: 0' : ''}
          </span>
          ${e.verificado_at ? '<span class="glass-pill text-xs text-emerald-600 px-2 py-0.5 rounded-full">Guardado</span>' : ''}
        </div>
        <h4 class="font-semibold text-slate-800 leading-snug">${escapeHtml(tienda.nombre)}</h4>
        <p class="text-xs text-slate-400 mt-1">${verificado}</p>
      </div>
      <div class="glass-card-inner p-3">
        <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Script</p>
        <p class="script-llamada text-sm text-slate-600 leading-relaxed italic">${escapeHtml(scriptLlamada(nombreVerificador()))}</p>
      </div>
      <div class="flex items-center justify-between gap-3 glass-card-inner p-3">
        <div>
          <p class="text-xs font-medium text-slate-600 uppercase tracking-wide">IVR Vale</p>
          <p class="text-xs text-slate-400">Paso 1 · ✓ = 1 · ✗ = 0</p>
        </div>
        <div class="flex gap-2 shrink-0">
          <button type="button" data-val-btn="${tienda.id}" data-val="1" onclick="seleccionarVal('${tienda.id}', true)"
            class="w-10 h-10 rounded-xl font-semibold text-base transition ${claseValBoton(b.funciona, true)}" title="Marcar 1">✓</button>
          <button type="button" data-val-btn="${tienda.id}" data-val="0" onclick="seleccionarVal('${tienda.id}', false)"
            class="w-10 h-10 rounded-xl font-semibold text-base transition ${claseValBoton(b.funciona, false)}" title="Marcar 0">✗</button>
        </div>
      </div>
      <div>
        <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Sugerencias · Paso 2</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2" id="sug-grid-${tienda.id}">
          ${htmlSugerencias(tienda.id, b.sugerencia)}
        </div>
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Detalle gestión · Paso 3</label>
        <textarea id="gestion-${tienda.id}" rows="2" placeholder="Nota operativa adicional..."
          class="glass-textarea w-full px-3 py-2 text-sm">${escapeHtml(b.gestion)}</textarea>
      </div>
      <div class="glass-card-inner p-3">
        <label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Auditoría · Paso 4</label>
        <p class="text-xs text-slate-500 mb-2">Comentario de control de calidad.</p>
        <textarea id="auditoria-${tienda.id}" rows="3" placeholder="Observaciones del auditor..."
          class="glass-textarea w-full px-3 py-2 text-sm">${escapeHtml(b.auditoria)}</textarea>
      </div>
      <p id="checklist-${tienda.id}" class="text-xs text-slate-500 glass-card-inner px-3 py-2">${textoChecklist(b)}</p>
      <button type="button" onclick="guardarVerificacion('${tienda.id}')"
        class="w-full glass-btn glass-btn-active font-medium py-3 rounded-xl text-sm transition">
        Guardar verificación (un solo registro)
      </button>
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
  lista.forEach(t => {
    const g = document.getElementById(`gestion-${t.id}`);
    const a = document.getElementById(`auditoria-${t.id}`);
    g?.addEventListener('input', () => syncBorradorFromInputs(t.id));
    a?.addEventListener('input', () => syncBorradorFromInputs(t.id));
  });
}

function construirPayload(tiendaId) {
  syncBorradorFromInputs(tiendaId);
  const b = getBorrador(tiendaId);
  let comentario = '';
  if (b.sugerencia) {
    comentario = b.gestion ? `${b.sugerencia} — ${b.gestion}` : b.sugerencia;
  } else {
    comentario = b.gestion;
  }
  return {
    tienda_id: tiendaId,
    funciona: b.funciona,
    comentario,
    comentario_auditoria: b.auditoria,
    verificado_por: document.getElementById('verificador-ivr')?.value.trim() || 'Equipo de Tienda',
  };
}

async function guardarVerificacion(tiendaId) {
  const b = getBorrador(tiendaId);
  syncBorradorFromInputs(tiendaId);
  const status = document.getElementById(`status-${tiendaId}`);

  if (b.funciona !== true && b.funciona !== false) {
    status.textContent = '⚠️ Seleccione ✓ o ✗ antes de guardar';
    status.className = 'text-xs text-amber-600 font-medium';
    return;
  }
  if (!b.sugerencia) {
    status.textContent = '⚠️ Seleccione una sugerencia antes de guardar';
    status.className = 'text-xs text-amber-600 font-medium';
    return;
  }

  status.textContent = 'Guardando...';
  status.className = 'text-xs text-slate-500';

  try {
    const res = await fetch('/api/ivr/registrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(construirPayload(tiendaId)),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    delete borradores[tiendaId];
    const hora = new Date(data.created_at).toLocaleString('es-EC');
    let msg = `✅ Un registro guardado ${hora} · IVR Vale: ${data.ivr_vale}`;
    if (data.google_sheets_ok) msg += ' · Sheets ✓';
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
window.guardarVerificacion = guardarVerificacion;

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
  if (editarFunciona !== true && editarFunciona !== false) {
    editarFunciona = sugerencia.funciona;
  }
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