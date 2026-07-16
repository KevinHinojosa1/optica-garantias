let currentPage = 1;
let searchTimeout = null;
let tiendaActiva = '';
let ciudadActiva = '';
const TIENDAS = window.TIENDAS_DATA || [];
let CONTEO_TIENDAS = {};

const filtroCiudad = document.getElementById('filtro-ciudad');
const filtroTienda = document.getElementById('filtro-tienda');
const panelAtencion = document.getElementById('panel-atencion');
const tiendaSeleccionada = document.getElementById('tienda-seleccionada');
const buscador = document.getElementById('buscador');
const lista = document.getElementById('lista-clientes');
const loading = document.getElementById('loading');
const sinResultados = document.getElementById('sin-resultados');
const paginacion = document.getElementById('paginacion');
const regTienda = document.getElementById('reg-tienda');
const btnRegistrar = document.getElementById('btn-registrar');
const busquedaInfo = document.getElementById('busqueda-info');
const resumenCiudad = document.getElementById('resumen-ciudad');

function conteoTienda(nombre) {
  return CONTEO_TIENDAS[nombre] || 0;
}

function etiquetaTienda(nombre) {
  const n = conteoTienda(nombre);
  if (n > 0) return `🟢 ${nombre} — ${n} paciente${n === 1 ? '' : 's'}`;
  return `⚪ ${nombre} — Sin registros`;
}

function actualizarResumenCiudad(ciudad) {
  if (!resumenCiudad) return;
  if (!ciudad) {
    resumenCiudad.classList.add('hidden');
    return;
  }
  const locales = TIENDAS.filter(t => t.ciudad === ciudad);
  const conRegistros = locales.filter(t => conteoTienda(t.nombre) > 0).length;
  const sinRegistros = locales.length - conRegistros;
  const totalPacientes = locales.reduce((sum, t) => sum + conteoTienda(t.nombre), 0);
  resumenCiudad.classList.remove('hidden');
  resumenCiudad.innerHTML =
    `📊 <strong>${ciudad}</strong>: ${locales.length} locales · ` +
    `<span class="text-emerald-700">${conRegistros} con registros</span> · ` +
    `<span class="text-slate-500">${sinRegistros} sin registros</span>` +
    (totalPacientes ? ` · <strong>${totalPacientes}</strong> paciente(s) en total` : '');
}

function rebuildTiendaSelect(ciudad) {
  filtroTienda.innerHTML = '';
  if (!ciudad) {
    filtroTienda.disabled = true;
    filtroTienda.classList.add('bg-slate-50');
    filtroTienda.innerHTML = '<option value="">— Primero seleccione ciudad —</option>';
    actualizarResumenCiudad('');
    return;
  }

  const locales = TIENDAS.filter(t => t.ciudad === ciudad)
    .sort((a, b) => {
      const ca = conteoTienda(a.nombre);
      const cb = conteoTienda(b.nombre);
      if (ca > 0 && cb === 0) return -1;
      if (ca === 0 && cb > 0) return 1;
      return a.nombre.localeCompare(b.nombre, 'es');
    });

  filtroTienda.disabled = false;
  filtroTienda.classList.remove('bg-slate-50');
  filtroTienda.innerHTML = `<option value="">— Seleccione local de ${ciudad} (${locales.length}) —</option>`;

  locales.forEach(t => {
    const opt = document.createElement('option');
    const n = conteoTienda(t.nombre);
    opt.value = t.nombre;
    opt.textContent = etiquetaTienda(t.nombre);
    opt.dataset.conRegistros = n > 0 ? '1' : '0';
    opt.dataset.total = String(n);
    filtroTienda.appendChild(opt);
  });
  actualizarResumenCiudad(ciudad);
}

async function cargarConteoTiendas() {
  try {
    const res = await fetch('/api/clientes/conteo-por-tienda');
    if (!res.ok) return;
    CONTEO_TIENDAS = await res.json();
    if (ciudadActiva) rebuildTiendaSelect(ciudadActiva);
    if (tiendaActiva) onTiendaChange();
  } catch { /* conteo opcional */ }
}

function actualizarInfoBusqueda() {
  if (!busquedaInfo) return;
  const q = buscador.value.trim();

  if (!tiendaActiva) {
    busquedaInfo.innerHTML = 'Seleccione ciudad y local para ver pacientes de esa tienda';
    return;
  }
  if (q) {
    busquedaInfo.innerHTML = `🔎 Buscando <strong>"${escapeHtml(q)}"</strong> en <strong>${escapeHtml(tiendaActiva)}</strong>`;
  } else {
    const n = conteoTienda(tiendaActiva);
    const badge = n > 0
      ? `<span class="text-emerald-700">🟢 ${n} paciente${n === 1 ? '' : 's'}</span>`
      : '<span class="text-slate-500">⚪ Sin registros</span>';
    busquedaInfo.innerHTML = `🏪 <strong>${escapeHtml(tiendaActiva)}</strong> — ${escapeHtml(ciudadActiva)} · ${badge}`;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

filtroCiudad.addEventListener('change', () => {
  ciudadActiva = filtroCiudad.value;
  tiendaActiva = '';
  filtroTienda.value = '';
  regTienda.value = '';
  btnRegistrar.disabled = true;
  lista.innerHTML = '';
  paginacion.innerHTML = '';
  sinResultados.classList.add('hidden');

  rebuildTiendaSelect(ciudadActiva);

  if (ciudadActiva) {
    panelAtencion.classList.remove('hidden');
    activarTab('registrar');
    tiendaSeleccionada.classList.remove('hidden');
    tiendaSeleccionada.innerHTML = `📍 <strong>${ciudadActiva}</strong> — seleccione el local`;
  } else {
    panelAtencion.classList.add('hidden');
    tiendaSeleccionada.classList.add('hidden');
  }
  actualizarInfoBusqueda();
});

filtroTienda.addEventListener('change', onTiendaChange);

function onTiendaChange() {
  tiendaActiva = filtroTienda.value;

  if (tiendaActiva) {
    regTienda.value = tiendaActiva;
    btnRegistrar.disabled = false;
    const n = conteoTienda(tiendaActiva);
    const estadoReg = n > 0
      ? `<span class="text-emerald-700">🟢 ${n} paciente${n === 1 ? '' : 's'} registrado${n === 1 ? '' : 's'}</span>`
      : '<span class="text-slate-500">⚪ Sin registros aún — puede registrar el primero</span>';
    tiendaSeleccionada.innerHTML = `✅ Atendiendo en: <strong>${escapeHtml(tiendaActiva)}</strong> — ${escapeHtml(ciudadActiva)}<br>${estadoReg}`;
    currentPage = 1;
    if (!panelBuscar.classList.contains('hidden')) {
      cargarClientes();
    }
  } else {
    regTienda.value = '';
    btnRegistrar.disabled = true;
    lista.innerHTML = '';
    paginacion.innerHTML = '';
    sinResultados.classList.add('hidden');
    if (ciudadActiva) {
      tiendaSeleccionada.innerHTML = `📍 <strong>${ciudadActiva}</strong> — seleccione el local`;
    }
  }
  actualizarInfoBusqueda();
}

const tabBuscar = document.getElementById('tab-buscar');
const tabRegistrar = document.getElementById('tab-registrar');
const panelBuscar = document.getElementById('panel-buscar');
const panelRegistrar = document.getElementById('panel-registrar');

tabBuscar.addEventListener('click', () => activarTab('buscar'));
tabRegistrar.addEventListener('click', () => activarTab('registrar'));

function activarTab(tab) {
  if (tab === 'buscar') {
    if (!tiendaActiva) {
      alert('Seleccione primero la ciudad y el local para buscar pacientes de esa tienda.');
      return;
    }
    tabBuscar.className = 'tab-btn shrink-0 px-4 sm:px-5 py-3 text-sm sm:text-base font-semibold text-optica-600 border-b-2 border-optica-600 whitespace-nowrap';
    tabRegistrar.className = 'tab-btn shrink-0 px-4 sm:px-5 py-3 text-sm sm:text-base font-semibold text-slate-400 border-b-2 border-transparent hover:text-slate-600 whitespace-nowrap';
    panelBuscar.classList.remove('hidden');
    panelRegistrar.classList.add('hidden');
    actualizarInfoBusqueda();
    cargarClientes();
  } else {
    tabRegistrar.className = 'tab-btn shrink-0 px-4 sm:px-5 py-3 text-sm sm:text-base font-semibold text-optica-600 border-b-2 border-optica-600 whitespace-nowrap';
    tabBuscar.className = 'tab-btn shrink-0 px-4 sm:px-5 py-3 text-sm sm:text-base font-semibold text-slate-400 border-b-2 border-transparent hover:text-slate-600 whitespace-nowrap';
    panelRegistrar.classList.remove('hidden');
    panelBuscar.classList.add('hidden');
  }
}

buscador.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentPage = 1;
    actualizarInfoBusqueda();
    cargarClientes();
  }, 300);
});
document.getElementById('btn-buscar').addEventListener('click', () => {
  currentPage = 1;
  actualizarInfoBusqueda();
  cargarClientes();
});

function buildSearchUrl() {
  const q = buscador.value.trim();
  const params = new URLSearchParams({
    page: String(currentPage),
    per_page: '20',
    tienda: tiendaActiva,
  });
  if (q) params.set('q', q);
  return `/api/clientes?${params.toString()}`;
}

async function cargarClientes() {
  if (!tiendaActiva) return;
  loading.classList.remove('hidden');
  lista.innerHTML = '';
  sinResultados.classList.add('hidden');

  try {
    const res = await fetch(buildSearchUrl());
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al cargar');
    loading.classList.add('hidden');

    if (!data.items.length) {
      sinResultados.classList.remove('hidden');
      paginacion.innerHTML = '';
      return;
    }

    if (!buscador.value.trim() && tiendaActiva) {
      CONTEO_TIENDAS[tiendaActiva] = data.total;
      actualizarInfoBusqueda();
      if (tiendaSeleccionada && !tiendaSeleccionada.classList.contains('hidden')) {
        onTiendaChange();
      }
    }
    lista.innerHTML = data.items.map(c => cardCliente(c)).join('');
    renderPaginacion(data.page, data.pages, data.total);
  } catch (err) {
    loading.classList.add('hidden');
    lista.innerHTML = `<div class="col-span-full bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">❌ ${err.message}</div>`;
  }
}

function cardCliente(c) {
  const dupBadge = c.es_duplicado
    ? '<span class="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">⚠️ DUPLICADO</span>'
    : '';
  const garBadge = `<span class="text-xs font-bold px-2 py-0.5 rounded-full ${c.dentro_garantia ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${c.dentro_garantia ? '✅ GARANTÍA' : '❌ FUERA'}</span>`;

  return `
    <div class="bg-white rounded-2xl shadow-sm border p-5 ${c.es_duplicado ? 'border-amber-300 bg-amber-50/30' : ''} hover:shadow-md transition">
      <div class="flex justify-between items-start mb-3 gap-2">
        <a href="/clientes/${c.id}" class="font-bold text-slate-800 hover:text-optica-600 flex-1">${escapeHtml(c.nombre)}</a>
        <div class="flex flex-col gap-1 items-end">${dupBadge}${garBadge}</div>
      </div>
      <a href="/clientes/${c.id}" class="block text-sm text-slate-500 space-y-1">
        <p>📋 ${escapeHtml(c.cedula)} · Factura ${escapeHtml(c.numero_factura)}</p>
        <p>🏪 ${escapeHtml(c.tienda)}</p>
        <p>👓 ${escapeHtml(c.producto)}</p>
        <p>📅 ${c.fecha_factura} · <strong>${c.dias_desde_factura} días</strong></p>
        ${c.tiene_ola_plus ? '<p class="text-blue-600 font-semibold">🛡️ OLA Plus</p>' : ''}
      </a>
      <div class="flex gap-2 mt-4 pt-3 border-t border-slate-100">
        <a href="/clientes/${c.id}" class="flex-1 text-center text-sm bg-optica-50 text-optica-700 hover:bg-optica-100 font-semibold py-2 rounded-lg transition">Ver ficha →</a>
        <button onclick="eliminarCliente(${c.id}, '${c.nombre.replace(/'/g, "\\'")}')" class="text-sm bg-red-50 text-red-600 hover:bg-red-100 font-semibold px-3 py-2 rounded-lg transition">🗑️</button>
      </div>
    </div>
  `;
}

async function eliminarCliente(id, nombre) {
  if (!confirm(`¿Eliminar al paciente "${nombre}"?\n\nEsta acción no se puede deshacer.`)) return;
  try {
    const res = await fetch(`/api/clientes/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    await cargarConteoTiendas();
    await cargarClientes();
  } catch (err) {
    alert('Error al eliminar: ' + err.message);
  }
}
window.eliminarCliente = eliminarCliente;

function renderPaginacion(page, pages, total) {
  const q = buscador.value.trim();
  const contexto = q ? `coincidencias en ${tiendaActiva}` : `en ${tiendaActiva}`;

  if (pages <= 1) {
    paginacion.innerHTML = `<span class="text-sm text-slate-500">${total} paciente(s) ${contexto}</span>`;
    return;
  }
  let html = `<span class="text-sm text-slate-400 mr-2">${total} total</span>`;
  if (page > 1) html += `<button onclick="irPagina(${page - 1})" class="px-3 py-1.5 rounded-lg bg-white border hover:bg-slate-50">← Ant</button>`;
  for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) {
    html += `<button onclick="irPagina(${i})" class="px-3 py-1.5 rounded-lg ${i === page ? 'bg-optica-600 text-white' : 'bg-white border hover:bg-slate-50'}">${i}</button>`;
  }
  if (page < pages) html += `<button onclick="irPagina(${page + 1})" class="px-3 py-1.5 rounded-lg bg-white border hover:bg-slate-50">Sig →</button>`;
  paginacion.innerHTML = html;
}

function irPagina(p) { currentPage = p; cargarClientes(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
window.irPagina = irPagina;

document.getElementById('form-registrar').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errDiv = document.getElementById('reg-error');
  errDiv.classList.add('hidden');

  if (!tiendaActiva) {
    errDiv.textContent = 'Seleccione ciudad y local antes de registrar.';
    errDiv.classList.remove('hidden');
    filtroCiudad.focus();
    return;
  }

  const payload = {
    nombre: document.getElementById('reg-nombre').value.trim(),
    cedula: document.getElementById('reg-cedula').value.trim(),
    telefono: document.getElementById('reg-telefono').value.trim(),
    tienda: tiendaActiva,
    producto: document.getElementById('reg-producto').value.trim(),
    tipo_producto: document.getElementById('reg-tipo').value,
    fecha_factura: document.getElementById('reg-fecha-factura').value,
    numero_factura: document.getElementById('reg-factura').value.trim(),
    fecha_entrega: document.getElementById('reg-fecha-entrega').value || null,
    tiene_ola_plus: document.getElementById('reg-ola-plus').checked,
    codigo_descuento: document.getElementById('reg-codigo-descuento').value
      ? Number(document.getElementById('reg-codigo-descuento').value) : null,
    porcentaje_descuento: document.getElementById('reg-pct-descuento').value
      ? Number(document.getElementById('reg-pct-descuento').value) : null,
  };

  btnRegistrar.disabled = true;
  btnRegistrar.textContent = 'Registrando...';

  try {
    const res = await fetch('/api/clientes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 409) {
        alert('⚠️ PACIENTE DUPLICADO\n\n' + (data.detail || 'Este paciente ya existe en la base de datos.'));
      }
      throw new Error(data.detail || 'Error al registrar');
    }
    window.location.href = `/clientes/${data.id}`;
  } catch (err) {
    errDiv.textContent = err.message;
    errDiv.classList.remove('hidden');
    btnRegistrar.disabled = false;
    btnRegistrar.textContent = 'Registrar paciente y continuar atención →';
  }
});

cargarConteoTiendas();