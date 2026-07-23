/**
 * Alertas Telegram — Matriz GENERAL operativa
 * Óptica Los Andes · Centro de Operaciones
 */

const META = window.ALERTAS_META || {};
let gridApi = null;
let filaSeleccionada = null;
let debounceTimer = null;
let chartsCargados = false;
let chartsVisibles = false;

const OPCIONES = {
  llamada: META.opciones_llamada || ['Pendiente', 'Sí', 'No', 'si', 'no'],
  contesto: META.opciones_contesto || ['Pendiente', 'Sí', 'No', 'si', 'no'],
  estado: META.opciones_estado || ['Sin gestión', 'En proceso', 'Resuelto', 'Pendiente llamada'],
  clasificacion: META.opciones_clasificacion || [],
};

const EDITABLES = new Set(META.columnas_editables || [
  'llamada_cliente', 'contesto', 'observacion_gestion', 'solucion',
  'clasificacion', 'estado_gestion', 'asesor', 'quien_llama', 'correos_disculpa',
]);

/* Columnas esenciales visibles; el resto en panel de columnas de ag-Grid (menú) */
const COLUMNAS_GRID = [
  { field: 'n', headerName: '#', width: 70, pinned: 'left', checkboxSelection: true, headerCheckboxSelection: true },
  { field: 'fecha_alerta', headerName: 'Fecha', width: 100, pinned: 'left' },
  { field: 'local', headerName: 'Local', width: 130 },
  { field: 'cliente', headerName: 'Cliente', width: 130 },
  { field: 'contacto', headerName: 'Teléfono', width: 110 },
  { field: 'comentario', headerName: 'Comentario', flex: 1, minWidth: 180, wrapText: true, autoHeight: true },
  { field: 'clasificacion', headerName: 'Clasificación', width: 150, editable: true,
    cellEditor: 'agSelectCellEditor', cellEditorParams: { values: OPCIONES.clasificacion } },
  { field: 'estado_gestion', headerName: 'Estado', width: 120, editable: true,
    cellEditor: 'agSelectCellEditor', cellEditorParams: { values: OPCIONES.estado } },
  { field: 'llamada_cliente', headerName: 'Llamada', width: 100, editable: true,
    cellEditor: 'agSelectCellEditor', cellEditorParams: { values: OPCIONES.llamada } },
  { field: 'contesto', headerName: 'Contestó', width: 100, editable: true,
    cellEditor: 'agSelectCellEditor', cellEditorParams: { values: OPCIONES.contesto } },
  { field: 'asesor', headerName: 'Asesor', width: 120, editable: true },
  { field: 'observacion_gestion', headerName: 'Gestión', width: 180, editable: true, wrapText: true, autoHeight: true },
  { field: 'solucion', headerName: 'Solución', width: 160, editable: true, wrapText: true, autoHeight: true },
  /* Secundarias (ocultas por defecto — se activan en columnas del grid) */
  { field: 'mes', headerName: 'Mes', width: 80, hide: true },
  { field: 'area', headerName: 'Área', width: 100, hide: true },
  { field: 'optometra', headerName: 'Optómetra', width: 120, hide: true },
  { field: 'calificacion', headerName: 'Calif.', width: 70, hide: true },
  { field: 'pregunta', headerName: 'Pregunta', width: 160, hide: true, wrapText: true },
  { field: 'responde', headerName: 'Responde', width: 80, hide: true },
  { field: 'justificacion_ia', headerName: 'Justificación IA', width: 180, hide: true, wrapText: true },
  { field: 'quien_llama', headerName: 'Quien llama', width: 110, hide: true, editable: true },
  { field: 'correos_disculpa', headerName: 'Correos', width: 100, hide: true, editable: true },
  { field: 'dialogo_ia', headerName: 'Diálogo IA', width: 160, hide: true, wrapText: true },
  { field: 'clasificado_por', headerName: 'Clasif. por', width: 90, hide: true },
];

const CAMPOS_MODAL = [
  { field: 'llamada_cliente', label: 'Llamada cliente', type: 'select', options: OPCIONES.llamada },
  { field: 'contesto', label: 'Contestó', type: 'select', options: OPCIONES.contesto },
  { field: 'observacion_gestion', label: 'Observación / Gestión de llamadas', type: 'textarea' },
  { field: 'solucion', label: 'Solución', type: 'textarea' },
  { field: 'clasificacion', label: 'Clasificación', type: 'select', options: OPCIONES.clasificacion },
  { field: 'estado_gestion', label: 'Estado gestión', type: 'select', options: OPCIONES.estado },
  { field: 'asesor', label: 'Asesor', type: 'text' },
  { field: 'quien_llama', label: 'Quien llama', type: 'text' },
  { field: 'correos_disculpa', label: 'Correos disculpa', type: 'text' },
];

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function toast(msg, tipo = 'info') {
  const el = document.getElementById('toast-alertas');
  if (!el) return;
  el.textContent = msg;
  el.className = `fixed bottom-4 right-4 z-50 glass-card px-4 py-3 text-sm font-medium shadow-lg toast-${tipo}`;
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 4000);
}

function valoresMultiselect(id) {
  const sel = document.getElementById(id);
  return sel ? Array.from(sel.selectedOptions).map(o => o.value) : [];
}

function filtrosQuery() {
  const p = new URLSearchParams();
  const set = (k, v) => { if (v) p.set(k, v); };
  set('fecha_desde', document.getElementById('filtro-desde')?.value);
  set('fecha_hasta', document.getElementById('filtro-hasta')?.value);
  set('texto', document.getElementById('filtro-texto')?.value?.trim());
  if (document.getElementById('filtro-solo-pendientes')?.checked) p.set('solo_pendientes', 'true');
  const join = (id, key) => { const v = valoresMultiselect(id); if (v.length) p.set(key, v.join(',')); };
  join('filtro-meses', 'meses');
  join('filtro-locales', 'locales');
  join('filtro-areas', 'areas');
  join('filtro-clasificacion', 'clasificaciones');
  join('filtro-estados', 'estados');
  join('filtro-contesto', 'contesto');
  return p;
}

function urlConFiltros(base) {
  const q = filtrosQuery().toString();
  return q ? `${base}?${q}` : base;
}

async function cargarDatos() {
  const res = await fetch(urlConFiltros('/api/alertas'));
  if (!res.ok) throw new Error('Error al cargar alertas');
  const data = await res.json();
  document.getElementById('filtro-resumen').textContent =
    `Mostrando ${data.filtrado} de ${data.total} casos · Pendientes sin gestión: ${data.pendientes}`;
  const badge = document.getElementById('badge-pendientes');
  if (badge) badge.textContent = `⏳ ${data.pendientes} pendientes`;
  if (gridApi) gridApi.setGridOption('rowData', data.filas || []);
  return data;
}

async function cargarKpis() {
  const res = await fetch(urlConFiltros('/api/alertas/kpis'));
  if (!res.ok) return;
  const k = await res.json();
  document.getElementById('kpi-total').textContent = k.total_filtrado;
  document.getElementById('kpi-sin-gestion').textContent = k.sin_gestion;
  document.getElementById('kpi-resueltos').textContent = k.resueltos;
  document.getElementById('kpi-contesto').textContent = k.contesto_si;
}

async function cargarGraficos() {
  if (!chartsVisibles) return;
  const res = await fetch(urlConFiltros('/api/alertas/graficos'));
  if (!res.ok) return;
  const g = await res.json();
  const cfg = { responsive: true, displayModeBar: false };
  if (document.getElementById('chart-tendencia')) {
    Plotly.newPlot('chart-tendencia', g.tendencia.data, g.tendencia.layout, cfg);
  }
  if (document.getElementById('chart-problemas')) {
    Plotly.newPlot('chart-problemas', g.top_problemas.data, g.top_problemas.layout, cfg);
  }
  if (document.getElementById('chart-heatmap')) {
    Plotly.newPlot('chart-heatmap', g.heatmap.data, g.heatmap.layout, cfg);
  }
  if (document.getElementById('chart-donut')) {
    Plotly.newPlot('chart-donut', g.donut.data, g.donut.layout, cfg);
  }
  if (g.heatmap_mes_local && document.getElementById('chart-heatmap-mes')) {
    document.getElementById('wrap-heatmap-mes')?.classList.remove('hidden');
    Plotly.newPlot('chart-heatmap-mes', g.heatmap_mes_local.data, g.heatmap_mes_local.layout, cfg);
  }
  chartsCargados = true;
}

async function refrescarTodo() {
  const jobs = [cargarDatos(), cargarKpis()];
  if (chartsVisibles) jobs.push(cargarGraficos());
  await Promise.all(jobs);
  const exp = document.getElementById('btn-exportar');
  if (exp) exp.href = urlConFiltros('/api/alertas/exportar');
}

function actualizarPanelIaSeleccion() {
  const panel = document.getElementById('panel-ia');
  const label = document.getElementById('ia-caso-label');
  if (!label) return;
  if (filaSeleccionada) {
    panel?.classList.add('has-case');
    label.textContent =
      `Caso #${filaSeleccionada.n} — ${filaSeleccionada.cliente || 'Sin nombre'} · ${filaSeleccionada.local || ''}`;
  } else {
    panel?.classList.remove('has-case');
    label.textContent = 'Seleccione un caso en la matriz para generar WhatsApp o correo.';
  }
}

function initGrid() {
  const el = document.getElementById('alertas-grid');
  if (!el || typeof agGrid === 'undefined') return;
  gridApi = agGrid.createGrid(el, {
    columnDefs: COLUMNAS_GRID,
    rowData: [],
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
      minWidth: 70,
    },
    rowSelection: 'multiple',
    suppressRowClickSelection: false,
    animateRows: true,
    onSelectionChanged() {
      const rows = gridApi.getSelectedRows();
      filaSeleccionada = rows[0] || null;
      const res = document.getElementById('grid-resumen');
      if (res) {
        res.textContent = rows.length
          ? `${rows.length} seleccionado(s)${filaSeleccionada?.cliente ? ` · ${filaSeleccionada.cliente}` : ''}`
          : 'Seleccione un caso';
      }
      actualizarPanelIaSeleccion();
    },
    onRowDoubleClicked(ev) {
      filaSeleccionada = ev.data;
      actualizarPanelIaSeleccion();
      abrirModalEdicion();
    },
  });
}

function todasLasFilas() {
  const rows = [];
  gridApi?.forEachNode(n => { if (n.data) rows.push({ ...n.data }); });
  return rows;
}

function idsSeleccionados() {
  return (gridApi?.getSelectedRows() || []).map(r => Number(r.id));
}

async function guardarCambios() {
  const filas = todasLasFilas();
  const res = await fetch('/api/alertas/guardar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filas }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al guardar');
  toast(`✅ Guardado · ${data.actualizados} fila(s) actualizada(s)`, 'ok');
  await refrescarTodo();
}

const LOTE_IA = 8;

async function clasificar(endpoint, ids = null) {
  const payload = { ids: ids ?? idsSeleccionados() };
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error en clasificación');
  return data;
}

async function clasificarLotes(ids, onProgress) {
  let total = 0;
  for (let i = 0; i < ids.length; i += LOTE_IA) {
    const lote = ids.slice(i, i + LOTE_IA);
    const data = await clasificar('/api/alertas/clasificar-ia', lote);
    total += data.clasificadas || lote.length;
    if (onProgress) onProgress(Math.min(i + lote.length, ids.length), ids.length);
  }
  return total;
}

function mostrarProgresoUpload(done, total) {
  const panel = document.getElementById('upload-progreso');
  const bar = document.getElementById('upload-progreso-bar');
  const txt = document.getElementById('upload-progreso-texto');
  if (!panel || !bar || !txt) return;
  panel.classList.remove('hidden');
  const pct = total ? Math.round((done / total) * 100) : 0;
  bar.style.width = `${pct}%`;
  txt.textContent = `Clasificando con IA: ${done} / ${total} (${pct}%)`;
}

function ocultarProgresoUpload() {
  document.getElementById('upload-progreso')?.classList.add('hidden');
}

async function procesarExcel() {
  const input = document.getElementById('input-excel');
  const file = input?.files?.[0];
  if (!file) { toast('Seleccione un archivo Excel', 'info'); return; }

  const modo = document.getElementById('upload-modo')?.value || 'reemplazar';
  const autoIa = document.getElementById('upload-auto-ia')?.checked;
  const estado = document.getElementById('upload-estado');
  const btn = document.getElementById('btn-procesar-excel');

  const fd = new FormData();
  fd.append('archivo', file);
  if (estado) estado.textContent = 'Leyendo Excel...';
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`/api/alertas/subir-excel?modo=${modo}`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al subir Excel');

    toast(`✅ ${data.total} registros · ${data.nuevas} fila(s) procesada(s)`, 'ok');
    if (estado) estado.textContent = `${data.total} registros cargados`;

    await refrescarTodo();

    const ids = data.ids_pendientes_ia || [];
    if (autoIa && ids.length) {
      if (estado) estado.textContent = 'Clasificando con IA...';
      const total = await clasificarLotes(ids, mostrarProgresoUpload);
      toast(`🤖 Clasificación IA completada · ${total} fila(s)`, 'ok');
      await refrescarTodo();
    }
  } finally {
    ocultarProgresoUpload();
    if (btn) btn.disabled = false;
    if (estado && estado.textContent.startsWith('Clasificando')) {
      estado.textContent = 'Listo';
    }
  }
}

function contextoIa(fila) {
  return {
    modulo: 'alertas_telegram',
    caso_id: String(fila.id || fila.n || ''),
    cliente_nombre: fila.cliente || '{cliente}',
    telefono: fila.contacto || fila.telefono || '{telefono}',
    local: fila.local || '',
    asesor: fila.asesor || '',
    comentario_cliente: fila.comentario || '',
    problema: fila.pregunta || '',
    descripcion: fila.comentario || '',
    clasificacion: fila.clasificacion || '',
    estado: fila.estado_gestion || '',
    solucion_actual: fila.solucion || '',
    historial: fila.observacion_gestion || '',
    calificacion: String(fila.calificacion || ''),
    canal: document.getElementById('ia-canal')?.value || 'whatsapp',
    contexto_extra: document.getElementById('ia-contexto-extra')?.value?.trim() || '',
  };
}

function mostrarResultadoIa(resultado) {
  document.getElementById('ia-resultado').classList.remove('hidden');
  document.getElementById('ia-generado-por').textContent =
    `Generado con ${resultado.generado_por === 'claude' ? 'Claude AI' : 'Plantilla CX'}`;
  const dlg = document.getElementById('ia-dialogo');
  if (resultado.dialogo?.length) {
    dlg.classList.remove('hidden');
    dlg.innerHTML = resultado.dialogo.map(l => {
      const a = l.actor === 'asesor' ? '🧑‍💼 Asesor' : '👤 Cliente';
      return `<p><strong>${a}:</strong> ${escapeHtml(l.texto)}</p>`;
    }).join('');
  } else dlg.classList.add('hidden');
  document.getElementById('ia-whatsapp').value = resultado.mensaje_whatsapp || '';
  document.getElementById('ia-asunto').value = resultado.asunto_correo || '';
  document.getElementById('ia-correo').value = resultado.mensaje_correo || '';
  document.getElementById('ia-voz').value = resultado.mensaje_voz || '';
  document.getElementById('ia-nota').textContent = resultado.nota_asesor ? `💡 ${resultado.nota_asesor}` : '';
  const wa = document.getElementById('btn-wa-link');
  if (resultado.wa_link) { wa.href = resultado.wa_link; wa.classList.remove('hidden'); }
  else wa.classList.add('hidden');
  if (filaSeleccionada && gridApi) {
    filaSeleccionada.dialogo_ia = (resultado.dialogo || []).map(l =>
      `${l.actor === 'asesor' ? 'Asesor' : 'Cliente'}: ${l.texto}`).join('\n');
    gridApi.applyTransaction({ update: [filaSeleccionada] });
  }
}

async function generarRespuestaIa() {
  if (!filaSeleccionada) { toast('Seleccione una fila en la matriz', 'info'); return; }
  const res = await fetch('/api/ia/generar-respuesta', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contexto: contextoIa(filaSeleccionada), titulo_modulo: 'Alertas Telegram' }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error IA');
  mostrarResultadoIa(data);
  toast('Sugerencia generada con Claude', 'ok');
}

function abrirModalEdicion() {
  if (!filaSeleccionada) { toast('Seleccione una fila', 'info'); return; }
  const f = filaSeleccionada;
  document.getElementById('modal-subtitulo').textContent =
    `#${f.n} · ${f.cliente || 'Sin cliente'} · ${f.local || ''} — ${(f.comentario || '').slice(0, 120)}`;
  const cont = document.getElementById('modal-campos');
  cont.innerHTML = CAMPOS_MODAL.map(c => {
    const val = escapeHtml(f[c.field] ?? '');
    if (c.type === 'textarea') {
      return `<div class="sm:col-span-2"><label class="block text-xs font-medium text-slate-500 mb-1">${c.label}</label>
        <textarea data-field="${c.field}" rows="3" class="glass-textarea w-full px-3 py-2 text-sm">${val}</textarea></div>`;
    }
    if (c.type === 'select') {
      const opts = c.options.map(o =>
        `<option value="${escapeHtml(o)}" ${o === f[c.field] ? 'selected' : ''}>${escapeHtml(o)}</option>`).join('');
      return `<div><label class="block text-xs font-medium text-slate-500 mb-1">${c.label}</label>
        <select data-field="${c.field}" class="glass-input w-full px-3 py-2 text-sm">${opts}</select></div>`;
    }
    return `<div><label class="block text-xs font-medium text-slate-500 mb-1">${c.label}</label>
      <input data-field="${c.field}" value="${val}" class="glass-input w-full px-3 py-2 text-sm"></div>`;
  }).join('');
  document.getElementById('modal-editar').classList.remove('hidden');
}

function cerrarModal() {
  document.getElementById('modal-editar').classList.add('hidden');
}

function guardarModalEnGrid() {
  if (!filaSeleccionada || !gridApi) return;
  document.querySelectorAll('#modal-campos [data-field]').forEach(el => {
    filaSeleccionada[el.dataset.field] = el.value;
  });
  gridApi.applyTransaction({ update: [filaSeleccionada] });
  cerrarModal();
  toast('Cambios aplicados en la matriz — pulse Guardar para persistir', 'info');
}

function limpiarFiltros() {
  document.getElementById('filtro-desde').value = META.fecha_min || '';
  document.getElementById('filtro-hasta').value = META.fecha_max || '';
  document.getElementById('filtro-texto').value = '';
  document.getElementById('filtro-solo-pendientes').checked = false;
  ['filtro-meses', 'filtro-locales', 'filtro-areas', 'filtro-clasificacion', 'filtro-estados', 'filtro-contesto']
    .forEach(id => { const s = document.getElementById(id); if (s) Array.from(s.options).forEach(o => { o.selected = false; }); });
  refrescarTodo();
}

function cerrarMenus() {
  document.getElementById('menu-mas-acciones')?.classList.add('hidden');
  document.getElementById('btn-mas-acciones')?.setAttribute('aria-expanded', 'false');
}

function togglePanel(panelId, btnId, openClass = 'is-open') {
  const panel = document.getElementById(panelId);
  const btn = document.getElementById(btnId);
  if (!panel) return;
  const open = panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !open);
  btn?.classList.toggle(openClass, open);
  btn?.setAttribute('aria-expanded', open ? 'true' : 'false');
  return open;
}

function bindEventos() {
  document.getElementById('btn-toggle-carga')?.addEventListener('click', () => {
    togglePanel('panel-subir-excel', 'btn-toggle-carga');
  });

  document.getElementById('btn-toggle-filtros')?.addEventListener('click', () => {
    const open = togglePanel('panel-filtros-extra', 'btn-toggle-filtros');
    const b = document.getElementById('btn-toggle-filtros');
    if (b) b.textContent = open ? 'Filtros ▴' : 'Filtros ▾';
  });

  document.getElementById('btn-mas-acciones')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const menu = document.getElementById('menu-mas-acciones');
    const btn = document.getElementById('btn-mas-acciones');
    const open = menu?.classList.contains('hidden');
    menu?.classList.toggle('hidden', !open);
    btn?.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  document.addEventListener('click', (e) => {
    const menu = document.getElementById('menu-mas-acciones');
    const btn = document.getElementById('btn-mas-acciones');
    if (!menu || menu.classList.contains('hidden')) return;
    if (btn?.contains(e.target) || menu.contains(e.target)) return;
    cerrarMenus();
  });

  document.getElementById('btn-toggle-charts')?.addEventListener('click', async () => {
    cerrarMenus();
    chartsVisibles = !chartsVisibles;
    document.getElementById('panel-charts')?.classList.toggle('hidden', !chartsVisibles);
    if (chartsVisibles) {
      toast('Cargando gráficos…', 'info');
      try {
        await cargarGraficos();
      } catch (e) {
        toast(e.message, 'error');
      }
    }
  });

  document.getElementById('btn-limpiar-filtros')?.addEventListener('click', limpiarFiltros);
  document.getElementById('btn-guardar')?.addEventListener('click', () => guardarCambios().catch(e => toast(e.message, 'error')));
  document.getElementById('btn-clasificar-reglas')?.addEventListener('click', () => {
    cerrarMenus();
    clasificar('/api/alertas/clasificar-reglas').then(d => {
      toast(`Clasificadas ${d.clasificadas} fila(s)`, 'ok');
      return refrescarTodo();
    }).catch(e => toast(e.message, 'error'));
  });
  document.getElementById('btn-clasificar-ia')?.addEventListener('click', async () => {
    cerrarMenus();
    try {
      const ids = idsSeleccionados();
      const total = ids.length
        ? (await clasificar('/api/alertas/clasificar-ia', ids)).clasificadas
        : await clasificarLotes(
          (await (await fetch('/api/alertas')).json()).filas.map(r => Number(r.id)),
          null,
        );
      toast(`Clasificadas ${total} fila(s) con IA`, 'ok');
      await refrescarTodo();
    } catch (e) { toast(e.message, 'error'); }
  });
  document.getElementById('btn-procesar-excel')?.addEventListener('click', () =>
    procesarExcel().catch(e => toast(e.message, 'error')));
  document.getElementById('btn-generar-dialogo')?.addEventListener('click', () =>
    generarRespuestaIa().catch(e => toast(e.message, 'error')));
  document.getElementById('btn-claude-fila')?.addEventListener('click', () => {
    cerrarMenus();
    document.getElementById('panel-ia')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    generarRespuestaIa().catch(e => toast(e.message, 'error'));
  });
  document.getElementById('btn-editar-fila')?.addEventListener('click', () => {
    cerrarMenus();
    abrirModalEdicion();
  });
  document.getElementById('btn-copiar-wa')?.addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('ia-whatsapp')?.value || '');
    toast('Copiado', 'ok');
  });
  document.getElementById('modal-cerrar')?.addEventListener('click', cerrarModal);
  document.getElementById('modal-guardar')?.addEventListener('click', guardarModalEnGrid);
  document.getElementById('modal-claude')?.addEventListener('click', () => generarRespuestaIa().catch(e => toast(e.message, 'error')));
  document.getElementById('btn-recargar-excel')?.addEventListener('click', async () => {
    cerrarMenus();
    if (!confirm('¿Recargar datos desde Excel? Se conservan las ediciones guardadas por ID.')) return;
    try {
      const res = await fetch('/api/alertas/recargar-excel', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error');
      toast(`Excel recargado · ${data.total} registros`, 'ok');
      await refrescarTodo();
    } catch (e) {
      toast(e.message, 'error');
    }
  });
  ['filtro-desde', 'filtro-hasta', 'filtro-texto', 'filtro-solo-pendientes',
    'filtro-meses', 'filtro-locales', 'filtro-areas', 'filtro-clasificacion', 'filtro-estados', 'filtro-contesto']
    .forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => refrescarTodo().catch(e => toast(e.message, 'error')), 350);
      });
      document.getElementById(id)?.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => refrescarTodo().catch(e => toast(e.message, 'error')), 350);
      });
    });
}

document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  bindEventos();
  refrescarTodo().catch(e => toast(e.message, 'error'));
});