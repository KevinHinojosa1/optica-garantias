const loading = document.getElementById('loading');
const tabla = document.getElementById('tabla-historial');
const tbody = document.getElementById('historial-body');
const sinHistorial = document.getElementById('sin-historial');
const contadorHistorial = document.getElementById('contador-historial');

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text ?? '';
  return div.innerHTML;
}

function badgeVeredicto(veredicto) {
  const color = veredicto === 'APLICA' ? 'text-green-700 bg-green-50'
    : veredicto === 'NO APLICA' ? 'text-red-700 bg-red-50'
    : 'text-yellow-700 bg-yellow-50';
  return `<span class="text-xs font-bold px-2 py-1 rounded-full ${color}">${escapeHtml(veredicto)}</span>`;
}

async function cargarHistorial() {
  try {
    const res = await fetch('/api/historial?limit=200');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al cargar');

    loading.classList.add('hidden');

    if (contadorHistorial) {
      contadorHistorial.textContent = `${data.length} consulta(s)`;
    }

    if (!data.length) {
      sinHistorial.classList.remove('hidden');
      tabla.classList.add('hidden');
      return;
    }

    sinHistorial.classList.add('hidden');
    tabla.classList.remove('hidden');
    tbody.innerHTML = data.map(h => `
      <tr class="border-t hover:bg-slate-50" id="fila-historial-${h.id}">
        <td class="px-4 py-3 whitespace-nowrap">${new Date(h.created_at).toLocaleString('es-EC')}</td>
        <td class="px-4 py-3 font-medium">${escapeHtml(h.cliente_nombre)}</td>
        <td class="px-4 py-3">${badgeVeredicto(h.veredicto)}</td>
        <td class="px-4 py-3 text-slate-500 max-w-xs truncate" title="${escapeHtml(h.motivo || '')}">${escapeHtml(h.motivo || '—')}</td>
        <td class="px-4 py-3">${escapeHtml(h.asesor)}</td>
        <td class="px-4 py-3 text-slate-500 text-xs">
          ${h.codigo_descuento ? `Cód. ${h.codigo_descuento}%` : '—'}
          ${h.porcentaje_descuento ? `<br>Aplic. ${h.porcentaje_descuento}%` : ''}
        </td>
        <td class="px-4 py-3 text-right whitespace-nowrap">
          <div class="inline-flex flex-col sm:flex-row gap-1 sm:gap-0">
            <a href="/api/historial/${h.id}/pdf" target="_blank"
              class="text-xs sm:text-sm bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold px-2.5 sm:px-3 py-1.5 rounded-lg transition inline-block sm:mr-1">
              📄 PDF
            </a>
            <button data-id="${h.id}" data-nombre="${escapeHtml(h.cliente_nombre)}"
              class="btn-eliminar-consulta text-xs sm:text-sm bg-red-50 text-red-600 hover:bg-red-100 font-semibold px-2.5 sm:px-3 py-1.5 rounded-lg transition">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    loading.classList.add('hidden');
    sinHistorial.classList.remove('hidden');
    sinHistorial.innerHTML = `<p class="text-red-600">❌ ${err.message}</p>`;
  }
}

tbody.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-eliminar-consulta');
  if (btn) eliminarConsulta(Number(btn.dataset.id), btn.dataset.nombre);
});

async function eliminarConsulta(id, nombre) {
  if (!confirm(`¿Eliminar la consulta de garantía de "${nombre}"?\n\nEsta acción no se puede deshacer.`)) return;
  try {
    const res = await fetch(`/api/historial/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    document.getElementById(`fila-historial-${id}`)?.remove();
    const filas = tbody.querySelectorAll('tr').length;
    if (contadorHistorial) contadorHistorial.textContent = `${filas} consulta(s)`;
    if (filas === 0) {
      tabla.classList.add('hidden');
      sinHistorial.classList.remove('hidden');
      sinHistorial.innerHTML = '<p class="text-4xl mb-2">📭</p><p>No hay consultas registradas</p>';
    }
  } catch (err) {
    alert('Error al eliminar: ' + err.message);
  }
}

document.getElementById('btn-limpiar-historial')?.addEventListener('click', async () => {
  if (!confirm('¿Eliminar TODAS las consultas de garantía del historial?\n\nEsta acción no se puede deshacer.')) return;
  try {
    const res = await fetch('/api/historial', { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    alert(data.mensaje);
    tbody.innerHTML = '';
    tabla.classList.add('hidden');
    sinHistorial.classList.remove('hidden');
    sinHistorial.innerHTML = '<p class="text-4xl mb-2">📭</p><p>No hay consultas registradas</p>';
    if (contadorHistorial) contadorHistorial.textContent = '0 consulta(s)';
  } catch (err) {
    alert('Error: ' + err.message);
  }
});

cargarHistorial();