/**
 * Base de Conocimiento — nutrir veredictos Claude
 */

const CATEGORIAS = Object.fromEntries((window.KB_CATEGORIAS || []).map(c => [c.id, c]));
let items = [];

function toast(msg, tipo = 'info') {
  const el = document.getElementById('toast-kb');
  if (!el) return;
  el.textContent = msg;
  el.className = `fixed bottom-4 right-4 z-50 glass-card px-4 py-3 text-sm font-medium shadow-lg border-l-4 ${
    tipo === 'ok' ? 'border-emerald-500 text-emerald-800' : tipo === 'error' ? 'border-red-500 text-red-800' : 'border-blue-500 text-blue-800'
  }`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 3500);
}

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function labelCategoria(id) {
  const c = CATEGORIAS[id];
  return c ? `${c.icon} ${c.label}` : id;
}

function resetForm() {
  document.getElementById('kb-id').value = '';
  document.getElementById('form-kb').reset();
  document.getElementById('kb-prioridad').value = '50';
  document.getElementById('kb-fuente').value = 'Óptica Los Andes';
  document.getElementById('kb-activo').checked = true;
  document.getElementById('kb-quitar-imagen').checked = false;
  document.getElementById('kb-preview').classList.add('hidden');
  document.getElementById('form-titulo').textContent = '➕ Nueva entrada';
  document.getElementById('btn-cancelar-kb').classList.add('hidden');
  document.getElementById('kb-imagen').value = '';
}

function llenarForm(item) {
  document.getElementById('kb-id').value = item.id;
  document.getElementById('kb-titulo').value = item.titulo;
  document.getElementById('kb-categoria').value = item.categoria;
  document.getElementById('kb-contenido').value = item.contenido;
  document.getElementById('kb-tags').value = item.tags || '';
  document.getElementById('kb-prioridad').value = item.prioridad;
  document.getElementById('kb-fuente').value = item.fuente;
  document.getElementById('kb-activo').checked = item.activo;
  document.getElementById('form-titulo').textContent = '✏️ Editar entrada';
  document.getElementById('btn-cancelar-kb').classList.remove('hidden');
  const prev = document.getElementById('kb-preview');
  const img = document.getElementById('kb-preview-img');
  if (item.imagen_url) {
    img.src = item.imagen_url;
    prev.classList.remove('hidden');
  } else {
    prev.classList.add('hidden');
  }
}

function renderLista(filtro = '') {
  const cont = document.getElementById('kb-lista');
  const q = filtro.trim().toLowerCase();
  const visibles = items.filter(i => {
    if (!q) return true;
    const blob = `${i.titulo} ${i.tags} ${i.contenido} ${i.categoria}`.toLowerCase();
    return blob.includes(q);
  });

  if (!visibles.length) {
    cont.innerHTML = '<p class="text-slate-400 text-sm py-8 text-center">No hay entradas. Agregue políticas oficiales o casos con imagen.</p>';
    return;
  }

  cont.innerHTML = visibles.map(i => `
    <div class="border rounded-xl p-4 ${i.activo ? 'bg-white' : 'bg-slate-50 opacity-75'} hover:shadow-sm transition">
      <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
        <div class="min-w-0 flex-1">
          <p class="font-semibold text-slate-800">${escapeHtml(i.titulo)}</p>
          <p class="text-xs text-slate-500 mt-0.5">${labelCategoria(i.categoria)} · Prioridad ${i.prioridad} · ${escapeHtml(i.fuente)}</p>
        </div>
        <span class="text-xs font-medium px-2 py-1 rounded-full ${i.activo ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'}">
          ${i.activo ? 'Activo' : 'Inactivo'}
        </span>
      </div>
      ${i.imagen_url ? `<img src="${i.imagen_url}" alt="" class="max-h-24 rounded-lg border mb-2">` : ''}
      <p class="text-sm text-slate-600 line-clamp-3">${escapeHtml(i.contenido)}</p>
      ${i.tags ? `<p class="text-xs text-optica-600 mt-2">🏷️ ${escapeHtml(i.tags)}</p>` : ''}
      <div class="flex gap-2 mt-3 pt-3 border-t border-slate-100">
        <button type="button" data-edit="${i.id}" class="text-xs font-semibold text-optica-600 hover:text-optica-800">✏️ Editar</button>
        <button type="button" data-del="${i.id}" class="text-xs font-semibold text-red-600 hover:text-red-800">🗑️ Eliminar</button>
      </div>
    </div>
  `).join('');

  cont.querySelectorAll('[data-edit]').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = items.find(x => x.id === Number(btn.dataset.edit));
      if (item) llenarForm(item);
    });
  });
  cont.querySelectorAll('[data-del]').forEach(btn => {
    btn.addEventListener('click', () => eliminar(Number(btn.dataset.del)));
  });
}

async function cargar() {
  const res = await fetch('/api/conocimiento');
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al cargar');
  items = data.items || [];
  document.getElementById('kb-contador').textContent = `${data.activos} activos / ${data.total} total`;
  renderLista(document.getElementById('kb-buscar')?.value || '');
}

async function guardar(e) {
  e.preventDefault();
  const id = document.getElementById('kb-id').value;
  const fd = new FormData();
  fd.append('titulo', document.getElementById('kb-titulo').value.trim());
  fd.append('categoria', document.getElementById('kb-categoria').value);
  fd.append('contenido', document.getElementById('kb-contenido').value.trim());
  fd.append('tags', document.getElementById('kb-tags').value.trim());
  fd.append('fuente', document.getElementById('kb-fuente').value.trim());
  fd.append('prioridad', document.getElementById('kb-prioridad').value);
  fd.append('activo', document.getElementById('kb-activo').checked ? 'true' : 'false');
  const file = document.getElementById('kb-imagen').files[0];
  if (file) fd.append('imagen', file);
  if (id) {
    fd.append('quitar_imagen', document.getElementById('kb-quitar-imagen').checked ? 'true' : 'false');
  }

  const url = id ? `/api/conocimiento/${id}` : '/api/conocimiento';
  const method = id ? 'PUT' : 'POST';
  const res = await fetch(url, { method, body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al guardar');
  toast(id ? 'Entrada actualizada' : 'Entrada creada', 'ok');
  resetForm();
  await cargar();
}

async function eliminar(id) {
  const item = items.find(i => i.id === id);
  if (!item || !confirm(`¿Eliminar "${item.titulo}"?`)) return;
  const res = await fetch(`/api/conocimiento/${id}`, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error');
  toast('Entrada eliminada', 'ok');
  await cargar();
}

document.getElementById('form-kb')?.addEventListener('submit', e => guardar(e).catch(err => toast(err.message, 'error')));
document.getElementById('btn-cancelar-kb')?.addEventListener('click', resetForm);
document.getElementById('kb-buscar')?.addEventListener('input', e => renderLista(e.target.value));
document.getElementById('kb-imagen')?.addEventListener('change', e => {
  const file = e.target.files[0];
  const prev = document.getElementById('kb-preview');
  const img = document.getElementById('kb-preview-img');
  if (file) {
    img.src = URL.createObjectURL(file);
    prev.classList.remove('hidden');
  }
});

cargar().catch(err => toast(err.message, 'error'));