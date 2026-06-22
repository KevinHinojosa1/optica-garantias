const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('archivo');
const fileName = document.getElementById('archivo-nombre');
const btnImportar = document.getElementById('btn-importar');
const form = document.getElementById('form-importar');
const resultado = document.getElementById('resultado');
const erroresDetalle = document.getElementById('errores-detalle');
const duplicadosDetalle = document.getElementById('duplicados-detalle');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('border-optica-500'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-optica-500'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('border-optica-500');
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    mostrarArchivo();
  }
});

fileInput.addEventListener('change', mostrarArchivo);

function mostrarArchivo() {
  if (fileInput.files.length) {
    fileName.textContent = fileInput.files[0].name;
    fileName.classList.remove('hidden');
    btnImportar.disabled = false;
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!fileInput.files.length) return;

  btnImportar.disabled = true;
  btnImportar.textContent = 'Importando...';
  resultado.classList.add('hidden');
  erroresDetalle.classList.add('hidden');
  duplicadosDetalle.classList.add('hidden');

  const formData = new FormData();
  formData.append('archivo', fileInput.files[0]);

  try {
    const res = await fetch('/api/importar', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Error al importar');

    resultado.classList.remove('hidden');
    resultado.innerHTML = `
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
        <div class="bg-blue-50 rounded-xl p-4">
          <p class="text-2xl font-bold text-blue-700">${data.total_filas}</p>
          <p class="text-xs text-blue-500">Total filas</p>
        </div>
        <div class="bg-green-50 rounded-xl p-4">
          <p class="text-2xl font-bold text-green-700">${data.registros_insertados}</p>
          <p class="text-xs text-green-500">Insertados</p>
        </div>
        <div class="bg-amber-50 rounded-xl p-4">
          <p class="text-2xl font-bold text-amber-700">${data.duplicados || 0}</p>
          <p class="text-xs text-amber-600">Duplicados</p>
        </div>
        <div class="bg-red-50 rounded-xl p-4">
          <p class="text-2xl font-bold text-red-700">${data.errores}</p>
          <p class="text-xs text-red-500">Errores</p>
        </div>
      </div>
      ${data.registros_insertados > 0 ? '<p class="text-center text-green-600 mt-4 font-semibold">✅ Importación completada. <a href="/clientes" class="underline">Ver clientes →</a></p>' : ''}
    `;

    if (data.duplicados > 0) {
      duplicadosDetalle.classList.remove('hidden');
      duplicadosDetalle.innerHTML = `
        <div class="bg-amber-50 border-2 border-amber-300 rounded-xl p-4 text-sm">
          <p class="font-bold text-amber-800 text-base mb-2">⚠️ ALERTA: ${data.duplicados} cliente(s) duplicado(s) detectado(s)</p>
          <p class="text-amber-700 mb-2">Estos registros <strong>NO fueron importados</strong> porque ya existen en la base de datos o se repiten en el archivo.</p>
          <details>
            <summary class="font-semibold text-amber-800 cursor-pointer">Ver detalle de duplicados</summary>
            <ul class="mt-2 space-y-1 text-amber-700 list-disc pl-5">${data.detalle_duplicados.map(d => `<li>${d}</li>`).join('')}</ul>
          </details>
        </div>
      `;
    }

    if (data.detalle_errores?.length) {
      erroresDetalle.classList.remove('hidden');
      erroresDetalle.innerHTML = `
        <details class="bg-red-50 border border-red-200 rounded-xl p-4 text-sm">
          <summary class="font-semibold text-red-700 cursor-pointer">Ver detalle de errores (${data.errores})</summary>
          <ul class="mt-2 space-y-1 text-red-600 list-disc pl-5">${data.detalle_errores.map(e => `<li>${e}</li>`).join('')}</ul>
        </details>
      `;
    }

    if (data.duplicados > 0 && data.registros_insertados === 0) {
      alert(`⚠️ Importación bloqueada: todos los registros son duplicados o tienen errores.\n\nDuplicados: ${data.duplicados}\nErrores: ${data.errores}`);
    }
  } catch (err) {
    resultado.classList.remove('hidden');
    resultado.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">❌ ${err.message}</div>`;
  } finally {
    btnImportar.disabled = false;
    btnImportar.textContent = 'Importar clientes';
  }
});

const resultadoCarpeta = document.getElementById('resultado-carpeta');

function mostrarResultadoImport(data, contenedor) {
  contenedor.classList.remove('hidden');
  contenedor.innerHTML = `
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
      <div class="bg-blue-50 rounded-xl p-4">
        <p class="text-2xl font-bold text-blue-700">${data.total_filas}</p>
        <p class="text-xs text-blue-500">Total filas</p>
      </div>
      <div class="bg-green-50 rounded-xl p-4">
        <p class="text-2xl font-bold text-green-700">${data.registros_insertados}</p>
        <p class="text-xs text-green-500">Insertados</p>
      </div>
      <div class="bg-amber-50 rounded-xl p-4">
        <p class="text-2xl font-bold text-amber-700">${data.duplicados || 0}</p>
        <p class="text-xs text-amber-600">Duplicados</p>
      </div>
      <div class="bg-red-50 rounded-xl p-4">
        <p class="text-2xl font-bold text-red-700">${data.errores}</p>
        <p class="text-xs text-red-500">Errores</p>
      </div>
    </div>
    ${data.registros_eliminados ? `<p class="text-center text-slate-500 text-sm mt-3">Se eliminaron ${data.registros_eliminados} registro(s) previos.</p>` : ''}
    ${data.registros_insertados > 0 ? '<p class="text-center text-green-600 mt-4 font-semibold">✅ Listo. <a href="/clientes" class="underline">Ir a Atención →</a></p>' : ''}
  `;
}

async function importarDesdeCarpeta(reemplazar) {
  const msg = reemplazar
    ? '¿Reemplazar toda la base con el Excel de la carpeta?\n\nSe borrarán todos los pacientes actuales.'
    : '¿Agregar pacientes del Excel de la carpeta?\n\nLos duplicados serán omitidos.';
  if (!confirm(msg)) return;

  resultadoCarpeta.classList.add('hidden');
  try {
    const res = await fetch(`/api/importar/carpeta?reemplazar=${reemplazar}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al importar');
    mostrarResultadoImport(data, resultadoCarpeta);
  } catch (err) {
    resultadoCarpeta.classList.remove('hidden');
    resultadoCarpeta.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">❌ ${err.message}</div>`;
  }
}

document.getElementById('btn-importar-carpeta')?.addEventListener('click', () => importarDesdeCarpeta(true));
document.getElementById('btn-agregar-carpeta')?.addEventListener('click', () => importarDesdeCarpeta(false));

document.getElementById('btn-limpiar')?.addEventListener('click', async () => {
  if (!confirm('¿Eliminar TODOS los pacientes de la base?\n\nEsta acción no se puede deshacer.')) return;
  try {
    const res = await fetch('/api/importar/limpiar', { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    resultadoCarpeta.classList.remove('hidden');
    resultadoCarpeta.innerHTML = `<div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-emerald-700">✅ ${data.mensaje}</div>`;
  } catch (err) {
    resultadoCarpeta.classList.remove('hidden');
    resultadoCarpeta.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">❌ ${err.message}</div>`;
  }
});