const formAnalisis = document.getElementById('form-analisis');
const dropImagen = document.getElementById('drop-imagen');
const imagenInput = document.getElementById('imagen');
const preview = document.getElementById('preview');
const resultadoAnalisis = document.getElementById('resultado-analisis');
const mensajeWhatsapp = document.getElementById('mensaje-whatsapp');
const btnRegenerar = document.getElementById('btn-regenerar');
const btnEnviarWa = document.getElementById('btn-enviar-wa');
const historialLateral = document.getElementById('historial-lateral');
const grupoDestino = document.getElementById('grupo-destino');
const veredictoReporte = document.getElementById('veredicto-reporte');
const panelReporte = document.getElementById('panel-reporte');

let ultimoAnalisis = null;
let ultimoHistorialId = null;
const btnEnviarPdfWa = document.getElementById('btn-enviar-pdf-wa');
const GRUPO_NUMERO = window.TIENDA_INFO?.whatsapp_grupo || '5931800678422';
const STORAGE_KEY = `ultimo_analisis_${window.CLIENTE_DATA?.id}`;

function guardarAnalisisLocal(analisis) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(analisis));
  } catch (_) { /* ignore */ }
}

function cargarAnalisisLocal() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

ultimoAnalisis = cargarAnalisisLocal();
if (ultimoAnalisis) {
  actualizarBadgeVeredicto(ultimoAnalisis.veredicto);
}

dropImagen.addEventListener('click', () => imagenInput.click());
imagenInput.addEventListener('change', () => {
  if (imagenInput.files.length) {
    preview.src = URL.createObjectURL(imagenInput.files[0]);
    preview.classList.remove('hidden');
  }
});

formAnalisis.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!imagenInput.files.length) {
    alert('Seleccione una imagen del daño.');
    return;
  }

  const btn = document.getElementById('btn-analizar');
  const modo = document.querySelector('input[name="modo-analisis"]:checked')?.value || 'conocimiento';
  btn.disabled = true;
  btn.textContent = modo === 'claude_total' ? '⏳ Claude total…' : '⏳ Claude + conocimiento…';
  resultadoAnalisis.classList.add('hidden');

  const formData = new FormData();
  formData.append('imagen', imagenInput.files[0]);
  const asesor = document.getElementById('asesor').value.trim() || window.DEFAULT_ASESOR || '';
  formData.append('asesor', asesor);
  formData.append('modo_analisis', modo);
  const codigo = document.getElementById('codigo-descuento')?.value;
  const pct = document.getElementById('porcentaje-descuento')?.value;
  if (codigo) formData.append('codigo_descuento', codigo);
  if (pct) formData.append('porcentaje_descuento', pct);

  const clienteId = document.getElementById('cliente-id').value;

  try {
    const res = await fetch(`/api/analizar/${clienteId}`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error en análisis');

    ultimoAnalisis = data.analisis;
    guardarAnalisisLocal(ultimoAnalisis);
    mostrarResultado(data.analisis);
    aplicarReporte(data.mensaje, data.wa_link, data.grupo_nombre, data.analisis.veredicto);
    if (data.historial_id) {
      ultimoHistorialId = data.historial_id;
      mostrarBotonPdf(data.pdf_url || `/api/historial/${data.historial_id}/pdf`, data.historial_id);
    }
    cargarHistorialLateral();

    panelReporte?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    resultadoAnalisis.classList.remove('hidden');
    resultadoAnalisis.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">❌ ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Analizar con Claude';
  }
});

function mostrarResultado(a) {
  const estilos = {
    'APLICA': 'bg-green-50 border-green-200 text-green-800',
    'NO APLICA': 'bg-red-50 border-red-200 text-red-800',
    'IMAGEN NO CLARA': 'bg-yellow-50 border-yellow-200 text-yellow-800',
  };
  const estilo = estilos[a.veredicto] || 'bg-slate-50 border-slate-200 text-slate-800';
  const fuentes = (a.fuentes_conocimiento || []).map(f =>
    `<li class="text-xs">${escapeHtml(f.titulo)}${f.tiene_imagen ? ' 🖼️' : ''}</li>`
  ).join('');
  const esKb = a.modo_analisis === 'conocimiento' || (a.fuentes_conocimiento || []).length;
  const bloqueKb = fuentes
    ? `<div class="bg-white/70 rounded-lg p-3 border border-white"><p class="text-xs font-semibold text-violet-800 mb-1">📚 Base de conocimiento consultada:</p><ul class="list-disc pl-4 space-y-0.5">${fuentes}</ul></div>`
    : (esKb
      ? '<p class="text-xs opacity-70">Sin documentos relevantes en la base. Nutra la <a href="/conocimiento" class="underline font-medium">Base de Conocimiento</a>.</p>'
      : '<p class="text-xs opacity-70">Modo <strong>Claude total</strong> — sin consulta a la base de conocimiento.</p>');
  const motorLabel = a.potenciado_por || (a.modo_analisis === 'claude_total' ? 'Claude total' : 'Claude');
  const motor = `<span class="text-xs font-medium text-violet-700 bg-violet-100 px-2 py-0.5 rounded-full">${escapeHtml(motorLabel)}</span>`;

  resultadoAnalisis.classList.remove('hidden');
  resultadoAnalisis.innerHTML = `
    <div class="${estilo} border rounded-xl p-5 space-y-3">
      <div class="flex justify-between items-center flex-wrap gap-2">
        <h4 class="font-bold text-lg">Veredicto: ${a.veredicto} ${motor}</h4>
        <span class="text-sm font-semibold bg-white px-3 py-1 rounded-full">Confianza: ${a.confianza}%</span>
      </div>
      <p><strong>Motivo:</strong> ${escapeHtml(a.motivo || '')}</p>
      <p><strong>Fundamento:</strong> ${escapeHtml(a.fundamento || '')}</p>
      ${bloqueKb}
      ${a.confianza < 70 ? '<p class="text-yellow-700 font-semibold">⚠️ Confianza baja — solicite una segunda foto con mejor iluminación.</p>' : ''}
      <p class="text-sm opacity-80">✅ El reporte del Módulo 4 se actualizó con este veredicto.</p>
    </div>
  `;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function actualizarBadgeVeredicto(veredicto) {
  if (!veredictoReporte || !veredicto) return;
  const estilos = {
    'APLICA': 'bg-green-100 text-green-800 border-green-300',
    'NO APLICA': 'bg-red-100 text-red-800 border-red-300',
    'IMAGEN NO CLARA': 'bg-yellow-100 text-yellow-800 border-yellow-300',
  };
  const estilo = estilos[veredicto] || 'bg-slate-100 text-slate-700 border-slate-300';
  veredictoReporte.className = `inline-flex items-center gap-1 text-sm font-bold px-3 py-1.5 rounded-full border ${estilo}`;
  veredictoReporte.innerHTML = `Veredicto: ${veredicto} <span class="text-violet-600 font-semibold">· Claude</span>`;
  veredictoReporte.classList.remove('hidden');
}

function actualizarEnlaceGrupo(waLink, grupoNombre) {
  btnEnviarWa.href = waLink;
  if (grupoDestino && grupoNombre) {
    grupoDestino.textContent = grupoNombre;
  }
}

function buildWaLink(mensaje) {
  const encoded = encodeURIComponent(mensaje);
  const num = GRUPO_NUMERO.replace(/\D/g, '');
  return `https://wa.me/${num}?text=${encoded}`;
}

function aplicarReporte(mensaje, waLink, grupoNombre, veredicto) {
  mensajeWhatsapp.value = mensaje;
  actualizarEnlaceGrupo(waLink, grupoNombre);
  actualizarBadgeVeredicto(veredicto);
  panelReporte?.classList.remove('ring-2', 'ring-optica-300');
  panelReporte?.classList.add('ring-2', 'ring-emerald-400');
  setTimeout(() => panelReporte?.classList.remove('ring-2', 'ring-emerald-400'), 2000);
}

async function generarMensajeDesdeAnalisis(analisis, mostrarErrores = true) {
  const asesor = document.getElementById('asesor')?.value.trim() || window.DEFAULT_ASESOR || '';
  const payload = {
    cliente_id: window.CLIENTE_DATA.id,
    analisis,
    asesor,
  };

  const res = await fetch('/api/mensajes/generar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    if (mostrarErrores) throw new Error(data.detail || 'Error al generar reporte');
    return null;
  }

  aplicarReporte(data.mensaje, data.wa_link, data.grupo_nombre, data.veredicto || analisis?.veredicto);
  return data;
}

btnRegenerar.addEventListener('click', async () => {
  const textoOriginal = btnRegenerar.textContent;
  btnRegenerar.disabled = true;
  btnRegenerar.textContent = '⏳ Regenerando...';

  try {
    let analisis = ultimoAnalisis || cargarAnalisisLocal();

    if (!analisis) {
      const resUltimo = await fetch(`/api/historial/ultimo/${window.CLIENTE_DATA.id}`);
      if (resUltimo.ok) {
        const h = await resUltimo.json();
        analisis = {
          veredicto: h.veredicto,
          motivo: h.motivo || '',
          fundamento: h.fundamento || '',
          confianza: h.confianza || 0,
        };
        ultimoAnalisis = analisis;
        guardarAnalisisLocal(analisis);
      }
    }

    if (!analisis) {
      alert('Primero analice una imagen con IA (Módulo 3) para generar un reporte con veredicto.');
      return;
    }

    await generarMensajeDesdeAnalisis(analisis);
  } catch (err) {
    alert('Error al regenerar reporte: ' + err.message);
  } finally {
    btnRegenerar.disabled = false;
    btnRegenerar.textContent = textoOriginal;
  }
});

mensajeWhatsapp.addEventListener('input', () => {
  btnEnviarWa.href = buildWaLink(mensajeWhatsapp.value);
});

async function cargarHistorialLateral() {
  try {
    const res = await fetch('/api/historial?limit=10');
    const data = await res.json();
    if (!data.length) {
      historialLateral.innerHTML = '<p class="text-slate-400">Sin consultas aún</p>';
      return;
    }
    historialLateral.innerHTML = data.map(h => `
      <div class="border-b pb-2">
        <p class="font-semibold text-slate-700">${escapeHtml(h.cliente_nombre)}</p>
        <p class="text-xs text-slate-500">${new Date(h.created_at).toLocaleString('es-EC')}</p>
        <span class="text-xs font-bold ${h.veredicto === 'APLICA' ? 'text-green-600' : h.veredicto === 'NO APLICA' ? 'text-red-600' : 'text-yellow-600'}">${h.veredicto}</span>
        <span class="text-xs text-slate-400"> · ${escapeHtml(h.asesor)}</span>
      </div>
    `).join('');
  } catch {
    historialLateral.innerHTML = '<p class="text-slate-400">Error al cargar</p>';
  }
}

async function restaurarUltimoReporte() {
  try {
    const res = await fetch(`/api/historial/ultimo/${window.CLIENTE_DATA.id}`);
    if (!res.ok) return;
    const h = await res.json();
    if (h.mensaje_enviado) {
      mensajeWhatsapp.value = h.mensaje_enviado;
      btnEnviarWa.href = buildWaLink(h.mensaje_enviado);
      actualizarBadgeVeredicto(h.veredicto);
      ultimoHistorialId = h.id;
      mostrarBotonPdf(`/api/historial/${h.id}/pdf`, h.id);
      ultimoAnalisis = {
        veredicto: h.veredicto,
        motivo: h.motivo || '',
        fundamento: h.fundamento || '',
        confianza: h.confianza || 0,
      };
      guardarAnalisisLocal(ultimoAnalisis);
    }
  } catch { /* sin historial previo */ }
}

function mostrarBotonPdf(url, historialId) {
  ultimoHistorialId = historialId;
  const btn = document.getElementById('btn-descargar-pdf');
  if (btn) {
    btn.href = url;
    btn.classList.remove('hidden');
    btn.title = `Informe consulta #${historialId}`;
  }
  if (btnEnviarPdfWa) {
    btnEnviarPdfWa.classList.remove('hidden');
    btnEnviarPdfWa.dataset.historialId = historialId;
  }
}

async function prepararMensajeConPdf(historialId, destino = 'tienda') {
  const res = await fetch('/api/mensajes/whatsapp-pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cliente_id: window.CLIENTE_DATA.id,
      historial_id: historialId,
      mensaje: mensajeWhatsapp.value.trim() || null,
      destino,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al preparar mensaje');
  return data;
}

function actualizarLabelsDestinoPdf() {
  const cli = document.getElementById('label-destino-cliente');
  const ti = document.getElementById('label-destino-tienda');
  const tel = window.CLIENTE_DATA?.telefono || '';
  const nombre = window.CLIENTE_DATA?.nombre || 'cliente';
  if (cli) {
    cli.textContent = tel
      ? `WhatsApp de ${nombre} · ${tel}`
      : 'Sin teléfono en la ficha — complete el número del cliente';
  }
  if (ti) {
    const g = window.TIENDA_INFO?.whatsapp_grupo_nombre || window.TIENDA_INFO?.nombre || 'Grupo de Apoyo';
    ti.textContent = g;
  }
}

function togglePanelDestinoPdf(mostrar) {
  const panel = document.getElementById('panel-destino-pdf');
  if (!panel) return;
  if (mostrar === undefined) {
    panel.classList.toggle('hidden');
  } else {
    panel.classList.toggle('hidden', !mostrar);
  }
  if (!panel.classList.contains('hidden')) actualizarLabelsDestinoPdf();
}

async function enviarReportePdfA(destino) {
  const historialId = ultimoHistorialId || Number(btnEnviarPdfWa?.dataset?.historialId);
  if (!historialId) {
    alert('Primero analice una imagen con IA para generar el PDF del informe.');
    return;
  }
  const btnCli = document.getElementById('btn-pdf-cliente');
  const btnTi = document.getElementById('btn-pdf-tienda');
  const botones = [btnCli, btnTi, btnEnviarPdfWa].filter(Boolean);
  botones.forEach(b => { b.disabled = true; });
  const textoBtn = btnEnviarPdfWa?.textContent;
  if (btnEnviarPdfWa) btnEnviarPdfWa.textContent = '⏳ Preparando…';
  try {
    const data = await prepararMensajeConPdf(historialId, destino);
    mensajeWhatsapp.value = data.mensaje;
    btnEnviarWa.href = data.wa_link;
    togglePanelDestinoPdf(false);
    window.open(data.wa_link, '_blank', 'noopener');
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    botones.forEach(b => { b.disabled = false; });
    if (btnEnviarPdfWa) btnEnviarPdfWa.textContent = textoBtn || '📤 Enviar reporte + PDF ▾';
  }
}

btnEnviarPdfWa?.addEventListener('click', (e) => {
  e.preventDefault();
  const historialId = ultimoHistorialId || Number(btnEnviarPdfWa.dataset.historialId);
  if (!historialId) {
    alert('Primero analice una imagen con IA para generar el PDF del informe.');
    return;
  }
  togglePanelDestinoPdf();
});

document.getElementById('btn-pdf-cliente')?.addEventListener('click', () => enviarReportePdfA('cliente'));
document.getElementById('btn-pdf-tienda')?.addEventListener('click', () => enviarReportePdfA('tienda'));
document.getElementById('btn-pdf-cerrar')?.addEventListener('click', () => togglePanelDestinoPdf(false));

document.getElementById('btn-guardar-descuento')?.addEventListener('click', async () => {
  const err = document.getElementById('descuento-error');
  const ok = document.getElementById('descuento-ok');
  err.classList.add('hidden');
  ok.classList.add('hidden');
  const codigoVal = document.getElementById('codigo-descuento').value;
  const pctVal = document.getElementById('porcentaje-descuento').value;
  try {
    const res = await fetch(`/api/clientes/${window.CLIENTE_DATA.id}/descuento`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        codigo_descuento: codigoVal ? Number(codigoVal) : null,
        porcentaje_descuento: pctVal ? Number(pctVal) : null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    window.CLIENTE_DATA.codigo_descuento = data.codigo_descuento;
    window.CLIENTE_DATA.porcentaje_descuento = data.porcentaje_descuento;
    ok.textContent = '✅ Descuento guardado correctamente.';
    ok.classList.remove('hidden');
  } catch (e) {
    err.textContent = e.message;
    err.classList.remove('hidden');
  }
});

cargarHistorialLateral();
restaurarUltimoReporte();

const btnEliminar = document.getElementById('btn-eliminar');
if (btnEliminar) {
  btnEliminar.addEventListener('click', async () => {
    const nombre = window.CLIENTE_DATA?.nombre || 'este cliente';
    if (!confirm(`¿Eliminar a "${nombre}"?\n\nEsta acción no se puede deshacer.`)) return;
    try {
      const res = await fetch(`/api/clientes/${window.CLIENTE_DATA.id}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      alert(data.mensaje || 'Cliente eliminado.');
      window.location.href = '/clientes';
    } catch (err) {
      alert('Error: ' + err.message);
    }
  });
}