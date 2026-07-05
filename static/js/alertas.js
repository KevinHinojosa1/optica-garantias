/**
 * Alertas Telegram — módulo FastAPI
 * Matriz editable, filtros, gráficos Plotly, clasificación e IA.
 */

const META = window.ALERTAS_META || {};
let gridApi = null;
let filasActuales = [];
let filaSeleccionada = null;
let debounceTimer = null;

const OPCIONES = {
  llamada: META.opciones_llamada || ['Pendiente', 'Sí', 'No'],
  contesto: META.opciones_contesto || ['Pendiente', 'Sí', 'No', 'No contesta'],
  estado: META.opciones_estado || ['Sin gestión', 'En proceso', 'Resuelto'],
  clasificacion: META.opciones_clasificacion || [],
};

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
  el._timer = setTimeout(() => el.classList.add('hidden'), 3500);
}

function valoresMultiselect(id) {
  const sel = document.getElementById(id);
  if (!sel) return [];
  return Array.from(sel.selectedOptions).map(o => o.value);
}

function filtrosQuery() {
  const params = new URLSearchParams();
  const desde = document.getElementById('filtro-desde')?.value;
  const hasta = document.getElementById('filtro-hasta')?.value;
  const texto = document.getElementById('filtro-texto')?.value?.trim() || '';
  const soloPend = document.getElementById('filtro-solo-pendientes')?.checked;

  if (desde) params.set('fecha_desde', desde);
  if (hasta) params.set('fecha_hasta', hasta);
  if (texto) params.set('texto', texto);
  if (soloPend) params.set('solo_pendientes', 'true');

  const locales = valoresMultiselect('filtro-locales');
  const areas = valoresMultiselect('filtro-areas');
  const clasif = valoresMultiselect('filtro-clasificacion');
  const estados = valoresMultiselect('filtro-estados');
  const contesto = valoresMultiselect('filtro-contesto');

  if (locales.length) params.set('locales', locales.join(','));
  if (areas.length) params.set('areas', areas.join(','));
  if (clasif.length) params.set('clasificaciones', clasif.join(','));
  if (estados.length) params.set('estados', estados.join(','));
  if (contesto.length) params.set('contesto', contesto.join(','));

  return params;
}

function urlConFiltros(base) {
  const q = filtrosQuery().toString();
  return q ? `${base}?${q}` : base;
}

async function cargarDatos() {
  const res = await fetch(urlConFiltros('/api/alertas'));
  if (!res.ok) throw new Error('Error al cargar alertas');
  const data = await res.json();
  filasActuales = data.filas || [];
  document.getElementById('filtro-resumen').textContent =
    `Mostrando ${data.filtrado} de ${data.total} casos · Pendientes: ${data.pendientes}`;
  document.getElementById('badge-pendientes').textContent = `⏳ Pendientes: ${data.pendientes}`;
  if (gridApi) {
    gridApi.setGridOption('rowData', filasActuales);
  }
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
  const res = await fetch(urlConFiltros('/api/alertas/graficos'));
  if (!res.ok) return;
  const g = await res.json();
  const cfg = { responsive: true, displayModeBar: false };
  Plotly.newPlot('chart-tendencia', g.tendencia.data, g.tendencia.layout, cfg);
  Plotly.newPlot('chart-problemas', g.top_problemas.data, g.top_problemas.layout, cfg);
  Plotly.newPlot('chart-heatmap', g.heatmap.data, g.heatmap.layout, cfg);
  Plotly.newPlot('chart-donut', g.donut.data, g.donut.layout, cfg);
}

async function refrescarTodo() {
  try {
    await Promise.all([cargarDatos(), cargarKpis(), cargarGraficos()]);
    document.getElementById('btn-exportar').href = urlConFiltros('/api/alertas/exportar');
  } catch (err) {
    toast(err.message || 'Error al actualizar', 'error');
  }
}

function columnDefs() {
  return [
    { field: 'id', headerName: 'ID', width: 70, pinned: 'left', checkboxSelection: true, headerCheckboxSelection: true },
    { field: 'fecha_alerta', headerName: 'Fecha', width: 130 },
    { field: 'local', headerName: 'Local', width: 130 },
    { field: 'area', headerName: 'Área', width: 120 },
    { field: 'problema', headerName: 'Problema', width: 180, wrapText: true, autoHeight: true },
    { field: 'cliente', headerName: 'Cliente', width: 120 },
    { field: 'telefono', headerName: 'Teléfono', width: 110 },
    { field: 'mensaje_telegram', headerName: 'Telegram', width: 200, wrapText: true, autoHeight: true },
    {
      field: 'llamada_cliente', headerName: 'Llamada', width: 110, editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: OPCIONES.llamada },
    },
    {
      field: 'contesto', headerName: 'Contestó', width: 110, editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: OPCIONES.contesto },
    },
    {
      field: 'clasificacion', headerName: 'Clasificación', width: 160, editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: OPCIONES.clasificacion },
    },
    {
      field: 'estado_gestion', headerName: 'Estado', width: 120, editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: OPCIONES.estado },
    },
    { field: 'solucion', headerName: 'Solución', width: 200, editable: true, wrapText: true, autoHeight: true },
    { field: 'asesor', headerName: 'Asesor', width: 110, editable: true },
    { field: 'dialogo_ia', headerName: 'Diálogo IA', width: 220, wrapText: true, autoHeight: true },
    { field: 'clasificado_por', headerName: 'Clasif. por', width: 100 },
  ];
}

function initGrid() {
  const el = document.getElementById('alertas-grid');
  if (!el || typeof agGrid === 'undefined') return;

  const gridOptions = {
    columnDefs: columnDefs(),
    rowData: [],
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
    },
    rowSelection: 'multiple',
    suppressRowClickSelection: false,
    animateRows: true,
    onSelectionChanged() {
      const rows = gridApi.getSelectedRows();
      filaSeleccionada = rows[0] || null;
      document.getElementById('grid-resumen').textContent =
        `Filas seleccionadas: ${rows.length}`;
      const label = document.getElementById('ia-caso-label');
      if (filaSeleccionada) {
        label.textContent = `Caso #${filaSeleccionada.id} — ${filaSeleccionada.cliente || 'Sin nombre'}`;
      } else {
        label.textContent = 'Seleccione una fila en la tabla para generar diálogo.';
      }
    },
    onCellValueChanged() {
      // cambios locales hasta guardar
    },
  };

  gridApi = agGrid.createGrid(el, gridOptions);
}

function idsSeleccionados() {
  if (!gridApi) return [];
  return gridApi.getSelectedRows().map(r => Number(r.id));
}

function todasLasFilasGrid() {
  if (!gridApi) return [];
  const rows = [];
  gridApi.forEachNode(node => {
    if (node.data) rows.push({ ...node.data });
  });
  return rows;
}

async function guardarCambios() {
  const filas = todasLasFilasGrid();
  const res = await fetch('/api/alertas/guardar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filas }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al guardar');
  toast(`Guardado · ${data.actualizados} fila(s) actualizada(s)`, 'ok');
  await refrescarTodo();
}

async function clasificar(endpoint) {
  const ids = idsSeleccionados();
  const body = { ids };
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error en clasificación');
  toast(`Clasificadas ${data.clasificadas} fila(s)`, 'ok');
  await refrescarTodo();
}

function contextoIaDesdeFila(fila) {
  return {
    modulo: 'alertas_telegram',
    caso_id: String(fila.id || ''),
    cliente_nombre: fila.cliente || '{cliente}',
    telefono: fila.telefono || '{telefono}',
    local: fila.local || '',
    asesor: fila.asesor || '',
    comentario_cliente: fila.mensaje_telegram || '',
    problema: fila.problema || '',
    descripcion: fila.descripcion || '',
    clasificacion: fila.clasificacion || '',
    estado: fila.estado_gestion || '',
    solucion_actual: fila.solucion || '',
    canal: document.getElementById('ia-canal')?.value || 'whatsapp',
    contexto_extra: document.getElementById('ia-contexto-extra')?.value?.trim() || '',
  };
}

function mostrarResultadoIa(resultado) {
  const panel = document.getElementById('ia-resultado');
  panel.classList.remove('hidden');

  const por = resultado.generado_por === 'claude' ? 'Claude AI' : 'Plantilla CX';
  document.getElementById('ia-generado-por').textContent = `Generado con ${por}`;

  const dialogoEl = document.getElementById('ia-dialogo');
  if (resultado.dialogo?.length) {
    dialogoEl.classList.remove('hidden');
    dialogoEl.innerHTML = resultado.dialogo.map(linea => {
      const actor = linea.actor === 'asesor' ? '🧑‍💼 Asesor' : '👤 Cliente';
      return `<p><strong>${actor}:</strong> ${escapeHtml(linea.texto)}</p>`;
    }).join('');
  } else {
    dialogoEl.classList.add('hidden');
  }

  document.getElementById('ia-whatsapp').value = resultado.mensaje_whatsapp || '';
  document.getElementById('ia-asunto').value = resultado.asunto_correo || '';
  document.getElementById('ia-correo').value = resultado.mensaje_correo || '';
  document.getElementById('ia-voz').value = resultado.mensaje_voz || '';
  document.getElementById('ia-nota').textContent = resultado.nota_asesor
    ? `💡 ${resultado.nota_asesor}` : '';

  const waLink = document.getElementById('btn-wa-link');
  if (resultado.wa_link) {
    waLink.href = resultado.wa_link;
    waLink.classList.remove('hidden');
  } else {
    waLink.classList.add('hidden');
  }

  if (filaSeleccionada && gridApi) {
    filaSeleccionada.dialogo_ia = (resultado.dialogo || [])
      .map(l => `${l.actor === 'asesor' ? 'Asesor' : 'Cliente'}: ${l.texto}`)
      .join('\n');
    filaSeleccionada.canal_dialogo = document.getElementById('ia-canal')?.value || 'whatsapp';
    gridApi.applyTransaction({ update: [filaSeleccionada] });
  }
}

async function generarRespuestaIa() {
  if (!filaSeleccionada) {
    toast('Seleccione una fila en la matriz', 'info');
    return;
  }
  const btn = document.getElementById('btn-generar-dialogo');
  const btn2 = document.getElementById('btn-sugerir-respuesta');
  btn.disabled = true;
  btn2.disabled = true;
  try {
    const res = await fetch('/api/ia/generar-respuesta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contexto: contextoIaDesdeFila(filaSeleccionada),
        titulo_modulo: 'Alertas Telegram',
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error IA');
    mostrarResultadoIa(data);
    toast('Respuesta generada', 'ok');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn2.disabled = false;
  }
}

function copiarTexto(texto) {
  navigator.clipboard.writeText(texto).then(() => toast('Copiado al portapapeles', 'ok'));
}

function programarRefresco() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => refrescarTodo(), 400);
}

function limpiarFiltros() {
  document.getElementById('filtro-desde').value = META.fecha_min || '';
  document.getElementById('filtro-hasta').value = META.fecha_max || '';
  document.getElementById('filtro-texto').value = '';
  document.getElementById('filtro-solo-pendientes').checked = false;
  ['filtro-locales', 'filtro-areas', 'filtro-clasificacion', 'filtro-estados', 'filtro-contesto']
    .forEach(id => {
      const sel = document.getElementById(id);
      if (sel) Array.from(sel.options).forEach(o => { o.selected = false; });
    });
  refrescarTodo();
}

function bindEventos() {
  document.getElementById('btn-limpiar-filtros')?.addEventListener('click', limpiarFiltros);
  document.getElementById('btn-guardar')?.addEventListener('click', () => guardarCambios().catch(e => toast(e.message, 'error')));
  document.getElementById('btn-clasificar-reglas')?.addEventListener('click', () =>
    clasificar('/api/alertas/clasificar-reglas').catch(e => toast(e.message, 'error')));
  document.getElementById('btn-clasificar-ia')?.addEventListener('click', () =>
    clasificar('/api/alertas/clasificar-ia').catch(e => toast(e.message, 'error')));
  document.getElementById('btn-generar-dialogo')?.addEventListener('click', generarRespuestaIa);
  document.getElementById('btn-sugerir-respuesta')?.addEventListener('click', generarRespuestaIa);
  document.getElementById('btn-copiar-wa')?.addEventListener('click', () => {
    copiarTexto(document.getElementById('ia-whatsapp')?.value || '');
  });

  const filtros = [
    'filtro-desde', 'filtro-hasta', 'filtro-texto', 'filtro-solo-pendientes',
    'filtro-locales', 'filtro-areas', 'filtro-clasificacion', 'filtro-estados', 'filtro-contesto',
  ];
  filtros.forEach(id => {
    document.getElementById(id)?.addEventListener('change', programarRefresco);
    document.getElementById(id)?.addEventListener('input', programarRefresco);
  });

  document.getElementById('input-importar')?.addEventListener('change', async (ev) => {
    const file = ev.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('archivo', file);
    try {
      const res = await fetch('/api/alertas/importar', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al importar');
      toast(`Importados ${data.importados} registros`, 'ok');
      await refrescarTodo();
    } catch (err) {
      toast(err.message, 'error');
    }
    ev.target.value = '';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  bindEventos();
  refrescarTodo();
});