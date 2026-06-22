const TIENDAS = window.TIENDAS_IVR || [];
const grid = document.getElementById('ivr-grid');
const historialDiv = document.getElementById('ivr-historial');
const inputVerificador = document.getElementById('verificador-ivr');
let ciudadFiltro = '';
let estados = {};

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

document.querySelectorAll('.filtro-ciudad').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filtro-ciudad').forEach(b => {
      b.className = 'filtro-ciudad shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-white hover:bg-slate-50 whitespace-nowrap';
    });
    btn.className = 'filtro-ciudad shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-optica-600 text-white whitespace-nowrap';
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

function cardTienda(tienda) {
  const e = estados[tienda.id] || {};
  const funciona = e.funciona;
  const verificado = e.verificado_at
    ? new Date(e.verificado_at).toLocaleString('es-EC')
    : 'Sin verificar esta semana';

  const btnOk = funciona === true
    ? 'bg-emerald-600 text-white ring-2 ring-emerald-300'
    : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200';
  const btnNo = funciona === false
    ? 'bg-red-600 text-white ring-2 ring-red-300'
    : 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200';

  return `
    <div class="bg-white rounded-2xl shadow-sm border p-5 flex flex-col gap-3" id="card-${tienda.id}">
      <div>
        <p class="text-xs font-semibold text-optica-600 uppercase">${escapeHtml(tienda.ciudad)}</p>
        <h4 class="font-bold text-slate-800">${escapeHtml(tienda.nombre)}</h4>
        <p class="text-xs text-slate-400 mt-1">Última verificación: ${verificado}</p>
      </div>
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
        <p class="text-xs font-semibold text-slate-500 uppercase mb-1">🎙️ Script de llamada</p>
        <p class="script-llamada text-sm text-slate-700 leading-relaxed italic">${escapeHtml(scriptLlamada(nombreVerificador()))}</p>
      </div>
      <div class="flex gap-2">
        <button onclick="marcarIvr('${tienda.id}', true)" class="flex-1 py-2.5 rounded-xl font-bold text-sm transition ${btnOk}">✓ Funciona</button>
        <button onclick="marcarIvr('${tienda.id}', false)" class="flex-1 py-2.5 rounded-xl font-bold text-sm transition ${btnNo}">✗ No funciona</button>
      </div>
      <textarea id="comentario-${tienda.id}" rows="2" placeholder="Comentario (opcional)..."
        class="w-full border rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-optica-500 outline-none">${escapeHtml(e.comentario || '')}</textarea>
      <p id="status-${tienda.id}" class="text-xs text-slate-400 min-h-[1rem]"></p>
    </div>
  `;
}

function renderGrid() {
  const lista = ciudadFiltro
    ? TIENDAS.filter(t => t.ciudad === ciudadFiltro)
    : TIENDAS;
  grid.innerHTML = lista.map(cardTienda).join('');
}

async function marcarIvr(tiendaId, funciona) {
  const comentario = document.getElementById(`comentario-${tiendaId}`)?.value || '';
  const verificadoPor = document.getElementById('verificador-ivr')?.value.trim() || 'Equipo de Tienda';
  const status = document.getElementById(`status-${tiendaId}`);
  status.textContent = 'Guardando...';
  status.className = 'text-xs text-slate-500';

  try {
    const res = await fetch('/api/ivr/registrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tienda_id: tiendaId,
        funciona,
        comentario,
        verificado_por: verificadoPor,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    const hora = new Date(data.created_at).toLocaleString('es-EC');
    let msg = `✅ Guardado ${hora}`;
    if (data.google_sheets_ok) msg += ' · Google Sheets ✓';
    else msg += ` · ${data.google_sheets_mensaje}`;
    status.textContent = msg;
    status.className = 'text-xs text-emerald-600 font-medium';

    await cargarEstado();
    cargarHistorialIvr();
  } catch (err) {
    status.textContent = '❌ ' + err.message;
    status.className = 'text-xs text-red-600';
  }
}
window.marcarIvr = marcarIvr;

let editarFunciona = true;
let historialRegistros = {};

const modalEditar = document.getElementById('modal-editar-ivr');
const editarStatus = document.getElementById('editar-ivr-status');

function actualizarBotonesEstadoEditar() {
  const btnSi = document.getElementById('editar-funciona-si');
  const btnNo = document.getElementById('editar-funciona-no');
  if (editarFunciona) {
    btnSi.className = 'flex-1 py-2.5 rounded-xl font-bold text-sm bg-emerald-600 text-white ring-2 ring-emerald-300';
    btnNo.className = 'flex-1 py-2.5 rounded-xl font-bold text-sm border border-red-200 bg-red-50 text-red-700';
  } else {
    btnSi.className = 'flex-1 py-2.5 rounded-xl font-bold text-sm border border-emerald-200 bg-emerald-50 text-emerald-700';
    btnNo.className = 'flex-1 py-2.5 rounded-xl font-bold text-sm bg-red-600 text-white ring-2 ring-red-300';
  }
}

function abrirModalEditar(registro) {
  document.getElementById('editar-ivr-id').value = registro.id;
  document.getElementById('modal-ivr-tienda').textContent =
    `${registro.tienda_nombre} (${registro.ciudad}) · ${new Date(registro.created_at).toLocaleString('es-EC')}`;
  document.getElementById('editar-comentario').value = registro.comentario || '';
  document.getElementById('editar-verificador').value =
    registro.verificado_por || document.getElementById('verificador-ivr')?.value.trim() || '';
  editarFunciona = registro.funciona;
  actualizarBotonesEstadoEditar();
  editarStatus.textContent = '';
  modalEditar.classList.remove('hidden');
}

function cerrarModalEditar() {
  modalEditar.classList.add('hidden');
}

async function guardarEdicionIvr() {
  const id = document.getElementById('editar-ivr-id').value;
  editarStatus.textContent = 'Guardando...';
  editarStatus.className = 'text-sm text-slate-500';
  try {
    const res = await fetch(`/api/ivr/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        funciona: editarFunciona,
        comentario: document.getElementById('editar-comentario').value,
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
        <table class="w-full text-xs sm:text-sm min-w-[640px]">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="text-left px-3 py-2">Fecha/Hora</th>
              <th class="text-left px-3 py-2">Tienda</th>
              <th class="text-left px-3 py-2">Estado</th>
              <th class="text-left px-3 py-2">Comentario</th>
              <th class="text-left px-3 py-2">Verificador</th>
              <th class="text-right px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(r => `
              <tr class="border-t hover:bg-slate-50/50">
                <td class="px-3 py-2 whitespace-nowrap">${new Date(r.created_at).toLocaleString('es-EC')}</td>
                <td class="px-3 py-2">${escapeHtml(r.tienda_nombre)} <span class="text-slate-400 text-xs">(${escapeHtml(r.ciudad)})</span></td>
                <td class="px-3 py-2 font-bold ${r.funciona ? 'text-emerald-600' : 'text-red-600'}">${r.funciona ? '✓ Funciona' : '✗ No funciona'}</td>
                <td class="px-3 py-2 text-slate-500 max-w-xs truncate" title="${escapeHtml(r.comentario || '')}">${escapeHtml(r.comentario || '—')}</td>
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

document.getElementById('editar-funciona-si')?.addEventListener('click', () => {
  editarFunciona = true;
  actualizarBotonesEstadoEditar();
});
document.getElementById('editar-funciona-no')?.addEventListener('click', () => {
  editarFunciona = false;
  actualizarBotonesEstadoEditar();
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