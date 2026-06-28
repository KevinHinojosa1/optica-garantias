const TIENDAS = window.TIENDAS_SCRIPTS || [];
const grid = document.getElementById('scripts-grid');
const filtroGrupos = document.getElementById('filtro-grupos');
let datos = { grupos: [] };
let grupoFiltro = '';
let fichaCargada = null;
let ultimoWaLink = '';
let ultimoWaMensaje = '';

const FASES = [
  { id: 'saludo', label: 'Saludo' },
  { id: 'intermedio', label: 'Intermedio' },
  { id: 'cierre', label: 'Cierre' },
];

const PLACEHOLDER = '…';

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t ?? '';
  return d.innerHTML;
}

function val(id) {
  return document.getElementById(id)?.value.trim() || '';
}

function tiendaIdPorNombre(nombreTienda) {
  if (!nombreTienda) return '';
  const exacta = TIENDAS.find(t => t.nombre === nombreTienda);
  if (exacta) return exacta.id;
  const parcial = TIENDAS.find(t =>
    nombreTienda.includes(t.nombre) || t.nombre.includes(nombreTienda)
  );
  return parcial?.id || '';
}

function construirFichaDesdeFormulario() {
  const sel = document.getElementById('var-tienda');
  const tiendaNombre = sel?.value
    ? sel.selectedOptions[0]?.textContent?.split(' (')[0] || ''
    : '';
  return {
    id: fichaCargada?.id ?? null,
    historial_id: fichaCargada?.historial_id ?? null,
    fuente: fichaCargada?.fuente || 'manual',
    nombre: val('var-cliente'),
    cedula: val('var-cedula'),
    telefono: val('var-telefono'),
    tienda: tiendaNombre || fichaCargada?.tienda || '',
    producto: val('var-producto'),
    tipo_producto: val('var-tipo-producto'),
    numero_factura: val('var-factura'),
    fecha_factura: val('var-fecha-factura'),
    fecha_entrega: fichaCargada?.fecha_entrega || null,
    tiene_ola_plus: fichaCargada?.tiene_ola_plus ?? false,
    codigo_descuento: fichaCargada?.codigo_descuento ?? null,
    porcentaje_descuento: fichaCargada?.porcentaje_descuento ?? null,
    dias_desde_factura: fichaCargada?.dias_desde_factura ?? null,
    dentro_garantia: fichaCargada?.dentro_garantia ?? null,
    estado_garantia: fichaCargada?.estado_garantia ?? null,
    veredicto: fichaCargada?.veredicto ?? null,
    motivo: fichaCargada?.motivo ?? null,
    fundamento: fichaCargada?.fundamento ?? null,
    confianza: fichaCargada?.confianza ?? null,
    fecha_prometida: val('var-fecha-prometida'),
    nueva_fecha: val('var-nueva-fecha'),
    motivo_operativo: val('var-motivo'),
  };
}

function grupoActivo() {
  if (!grupoFiltro) return null;
  return datos.grupos.find(g => g.id === grupoFiltro) || null;
}

function esPosventa() {
  return grupoFiltro === 'posventa';
}

function esGarantiaNoAprobada() {
  return grupoFiltro === 'garantia_no_aprobada';
}

function esModoSimple() {
  return !!grupoActivo()?.solo_asesor_cliente;
}

function variables() {
  if (esModoSimple()) {
    return {
      asesor: val('var-asesor') || PLACEHOLDER,
      cliente: val('var-cliente') || PLACEHOLDER,
    };
  }
  const f = construirFichaDesdeFormulario();
  const t = TIENDAS.find(x => x.nombre === f.tienda) || {};
  return {
    asesor: val('var-asesor') || PLACEHOLDER,
    cliente: f.nombre || PLACEHOLDER,
    cedula: f.cedula || PLACEHOLDER,
    telefono: f.telefono || PLACEHOLDER,
    tienda: f.tienda || PLACEHOLDER,
    ciudad: t.ciudad || PLACEHOLDER,
    direccion: t.direccion || PLACEHOLDER,
    producto: f.producto || PLACEHOLDER,
    tipo_producto: f.tipo_producto || PLACEHOLDER,
    factura: f.numero_factura || PLACEHOLDER,
    fecha_factura: f.fecha_factura || PLACEHOLDER,
    fecha_prometida: f.fecha_prometida || PLACEHOLDER,
    nueva_fecha: f.nueva_fecha || PLACEHOLDER,
    motivo: f.motivo_operativo || f.motivo || PLACEHOLDER,
  };
}

function personalizar(texto) {
  let r = texto || '';
  const v = variables();
  Object.entries(v).forEach(([k, val]) => {
    r = r.replaceAll(`{${k}}`, val);
  });
  return r;
}

function armarWhatsAppPosventa(plantilla) {
  const cuerpo = personalizar(plantilla);
  const asesor = val('var-asesor');
  const pie = [
    asesor ? `👨‍💼 *Asesor:* ${asesor}` : '',
    '💙 *Gracias por confiar en Óptica Los Andes*',
    '_Ante cualquier consulta, estamos para servirle._',
  ].filter(Boolean).join('\n');
  return {
    mensaje: `${cuerpo}\n\n${pie}`,
    wa_link: '',
    incluye_ficha: false,
  };
}

async function armarWhatsAppCompleto(plantilla) {
  if (esModoSimple()) {
    return armarWhatsAppPosventa(plantilla);
  }
  const ficha = construirFichaDesdeFormulario();
  const res = await fetch('/api/scripts/armar-whatsapp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cuerpo: plantilla,
      asesor: val('var-asesor'),
      ficha,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Error al armar WhatsApp');
  return data;
}

function copiarTexto(texto, btn) {
  navigator.clipboard.writeText(texto).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓ Copiado';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}
window.copiarTexto = copiarTexto;

function buscarEscenario(escId) {
  for (const grupo of datos.grupos) {
    const esc = grupo.escenarios.find(e => e.id === escId);
    if (esc) return { grupo, esc };
  }
  return null;
}

function nivelBadge(valor, label, color) {
  return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-semibold ${color}">
    ${label}: ${valor}/10
  </span>`;
}

function chipsLista(items, clase = 'bg-slate-100 text-slate-700') {
  return (items || []).map(t => `
    <button type="button" class="chip-copiar ${clase} text-xs rounded-lg px-2.5 py-1 hover:opacity-80 transition">
      ${escapeHtml(personalizar(t))}
    </button>
  `).join('');
}

function renderCxGuide(esc) {
  const cx = esc.cx;
  if (!cx) return '';

  const niveles = esc.niveles || {};
  const perfiles = (esc.perfil_emocional || []).map(p =>
    `<span class="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-lg font-medium">${escapeHtml(p)}</span>`
  ).join(' ');

  const evitar = (cx.evitar || []).map(e => `
    <tr class="border-b border-slate-100">
      <td class="py-2 pr-3 text-red-600 text-sm align-top">✗ ${escapeHtml(e.frase)}</td>
      <td class="py-2 text-emerald-700 text-sm align-top">→ ${escapeHtml(e.alternativa)}</td>
    </tr>
  `).join('');

  const guion = (cx.guion || []).map(l => {
    const esAsesor = l.actor === 'asesor';
    return `
      <div class="flex gap-2 ${esAsesor ? '' : 'opacity-90'}">
        <span class="text-xs font-bold uppercase shrink-0 w-14 ${esAsesor ? 'text-optica-600' : 'text-slate-500'}">
          ${esAsesor ? 'Asesor' : 'Cliente'}
        </span>
        <p class="text-sm text-slate-700">${escapeHtml(personalizar(l.texto))}</p>
      </div>
    `;
  }).join('');

  const objeciones = (cx.objeciones || []).map(o => `
    <div class="bg-white border rounded-xl p-3">
      <p class="text-xs font-bold text-amber-800 mb-1">${escapeHtml(o.situacion)}</p>
      <p class="text-sm text-slate-700">${escapeHtml(personalizar(o.respuesta))}</p>
    </div>
  `).join('');

  const variantes = cx.variantes || {};
  const tabsVar = Object.keys(variantes).map((k, i) => `
    <button type="button" data-variante="${k}"
      class="tab-variante px-2 py-1 rounded-lg text-xs font-semibold ${i === 0 ? 'bg-optica-600 text-white' : 'bg-slate-100 text-slate-600'}">
      ${escapeHtml(k.charAt(0).toUpperCase() + k.slice(1))}
    </button>
  `).join('');

  const primeraVar = Object.keys(variantes)[0] || '';

  return `
    <div class="cx-guide space-y-4 border-t border-slate-200 pt-4 mt-2">
      <div class="grid sm:grid-cols-2 gap-3 text-sm">
        <div class="bg-blue-50 border border-blue-100 rounded-xl p-3">
          <p class="text-xs font-bold text-blue-800 uppercase mb-1">Objetivo</p>
          <p class="text-slate-700">${escapeHtml(esc.objetivo || esc.descripcion)}</p>
        </div>
        <div class="bg-indigo-50 border border-indigo-100 rounded-xl p-3">
          <p class="text-xs font-bold text-indigo-800 uppercase mb-1">Perfil emocional</p>
          <div class="flex flex-wrap gap-1">${perfiles}</div>
          <div class="flex flex-wrap gap-1 mt-2">
            ${nivelBadge(niveles.empatia || 0, 'Empatía', 'bg-violet-100 text-violet-800')}
            ${nivelBadge(niveles.control || 0, 'Control', 'bg-sky-100 text-sky-800')}
            ${nivelBadge(niveles.fidelizacion || 0, 'Fidelización', 'bg-emerald-100 text-emerald-800')}
          </div>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-3 text-sm">
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Descubrimiento</p>
          <p class="text-slate-700 bg-slate-50 rounded-xl p-3">${escapeHtml(personalizar(cx.descubrimiento))}</p></div>
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Investigación</p>
          <p class="text-slate-700 bg-slate-50 rounded-xl p-3">${escapeHtml(personalizar(cx.investigacion))}</p></div>
      </div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Escucha activa</p>
        <div class="flex flex-wrap gap-1.5">${chipsLista(cx.escucha_activa, 'bg-teal-50 text-teal-800 border border-teal-100')}</div></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Validación emocional</p>
        <div class="flex flex-wrap gap-1.5">${chipsLista(cx.validacion_emocional, 'bg-violet-50 text-violet-800')}</div></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Solución</p>
        <p class="text-slate-700 bg-emerald-50 border border-emerald-100 rounded-xl p-3">${escapeHtml(personalizar(cx.solucion))}</p></div>

      <div class="grid md:grid-cols-2 gap-3">
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Técnicas para disminuir tensión</p>
          <ul class="text-sm text-slate-600 space-y-1 list-disc pl-4">${(cx.tecnicas_tension || []).map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul></div>
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Técnicas psicológicas</p>
          <div class="flex flex-wrap gap-1">${(cx.tecnicas_psicologicas || []).map(t =>
            `<span class="text-xs bg-slate-100 px-2 py-0.5 rounded-lg">${escapeHtml(t)}</span>`
          ).join('')}</div></div>
      </div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Palabras de tranquilidad</p>
        <div class="flex flex-wrap gap-1.5">${chipsLista(cx.palabras_tranquilidad, 'bg-sky-50 text-sky-800')}</div></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Qué NO decir → Alternativa</p>
        <table class="w-full text-left"><tbody>${evitar}</tbody></table></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Guion principal</p>
        <div class="bg-slate-50 border rounded-xl p-4 space-y-3">${guion}</div></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Manejo de objeciones</p>
        <div class="grid sm:grid-cols-2 gap-2">${objeciones}</div></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Variantes de respuesta</p>
        <div class="flex flex-wrap gap-1 mb-2">${tabsVar}</div>
        <p class="variante-texto text-sm text-slate-700 bg-slate-50 rounded-xl p-3 whitespace-pre-wrap">${escapeHtml(personalizar(variantes[primeraVar] || ''))}</p></div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-2">Fidelización</p>
        <div class="flex flex-wrap gap-1.5">${chipsLista(cx.fidelizacion, 'bg-emerald-50 text-emerald-800')}</div></div>

      <div class="grid md:grid-cols-2 gap-3 text-sm">
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Cierre perfecto</p>
          <p class="text-slate-700 bg-slate-50 rounded-xl p-3">${escapeHtml(personalizar(cx.cierre))}</p></div>
        <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Seguimiento</p>
          <p class="text-slate-700 bg-slate-50 rounded-xl p-3">${escapeHtml(personalizar(cx.seguimiento))}</p></div>
      </div>

      <div class="grid md:grid-cols-2 gap-3 text-sm">
        <div><p class="text-xs font-bold text-emerald-700 uppercase mb-1">Consejos para el asesor</p>
          <ul class="text-slate-600 space-y-1 list-disc pl-4">${(cx.consejos_asesor || []).map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul></div>
        <div><p class="text-xs font-bold text-red-700 uppercase mb-1">Errores comunes</p>
          <ul class="text-slate-600 space-y-1 list-disc pl-4">${(cx.errores_comunes || []).map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul></div>
      </div>

      <div><p class="text-xs font-bold text-slate-500 uppercase mb-1">Palabras clave</p>
        <div class="flex flex-wrap gap-1">${(cx.palabras_clave || []).map(k =>
          `<span class="text-xs font-semibold bg-optica-50 text-optica-700 px-2 py-0.5 rounded-lg">#${escapeHtml(k)}</span>`
        ).join('')}</div></div>
    </div>
  `;
}

function cardEscenario(grupo, esc) {
  const cardId = `card-${esc.id}`;
  const faseInicial = 'saludo';
  const textoInicial = personalizar(esc.fases[faseInicial].voz);
  const tieneCx = !!esc.cx;

  const tabsFase = FASES.map(f => `
    <button type="button" data-card="${cardId}" data-fase="${f.id}"
      class="tab-fase px-3 py-1.5 rounded-lg text-sm font-semibold transition ${f.id === faseInicial ? 'bg-optica-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}">
      ${f.label}
    </button>
  `).join('');

  const perfiles = (esc.perfil_emocional || []).slice(0, 3).map(p =>
    `<span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">${escapeHtml(p)}</span>`
  ).join('');

  return `
    <div class="bg-white rounded-2xl shadow-sm border p-5 flex flex-col gap-4" id="${cardId}"
      data-escenario-id="${escapeHtml(esc.id)}">
      <div>
        <p class="text-xs font-semibold text-optica-600 uppercase">${escapeHtml(grupo.titulo)}</p>
        <h4 class="font-bold text-slate-800 text-lg">${escapeHtml(esc.titulo)}</h4>
        <p class="text-sm text-slate-500 mt-1">${escapeHtml(esc.objetivo || esc.descripcion)}</p>
        ${perfiles ? `<div class="flex flex-wrap gap-1 mt-2">${perfiles}</div>` : ''}
      </div>
      <div class="flex flex-wrap gap-2">${tabsFase}</div>
      <div class="flex gap-2">
        <button type="button" data-card="${cardId}" data-canal="voz"
          class="tab-canal flex-1 py-2 rounded-xl text-sm font-bold transition bg-optica-600 text-white">🎙️ Voz</button>
        <button type="button" data-card="${cardId}" data-canal="whatsapp"
          class="tab-canal flex-1 py-2 rounded-xl text-sm font-bold transition bg-slate-100 text-slate-600 hover:bg-slate-200">💬 WhatsApp</button>
      </div>
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 min-h-[120px]">
        <p class="script-texto text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">${escapeHtml(textoInicial)}</p>
      </div>
      <p class="script-loading text-xs text-slate-400 hidden">Armando mensaje completo...</p>
      <div class="flex flex-wrap gap-2">
        <button type="button" onclick="copiarDesdeCard('${cardId}', this)"
          class="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
          📋 Copiar guión
        </button>
        <a href="#" target="_blank" rel="noopener"
          class="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white text-center transition link-wa">
          💬 Abrir WhatsApp
        </a>
      </div>
      ${tieneCx ? `
        <button type="button" data-card="${cardId}" class="btn-toggle-cx w-full py-2.5 rounded-xl text-sm font-semibold border-2 border-optica-200 text-optica-700 hover:bg-optica-50 transition">
          📖 Ver guía CX completa
        </button>
        <div class="cx-panel hidden">${renderCxGuide(esc)}</div>
      ` : ''}
    </div>
  `;
}

function estadoCard(card) {
  const faseActiva = card.querySelector('.tab-fase.bg-optica-600')?.dataset.fase || 'saludo';
  const canalActivo = card.querySelector('.tab-canal.bg-optica-600')?.dataset.canal || 'voz';
  return { faseActiva, canalActivo };
}

function enlazarChipsCopiar(contenedor) {
  contenedor?.querySelectorAll('.chip-copiar').forEach(btn => {
    btn.addEventListener('click', () => copiarTexto(btn.textContent.trim(), btn));
  });
}

function enlazarVariantes(card, esc) {
  const panel = card.querySelector('.cx-panel');
  if (!panel || !esc.cx?.variantes) return;
  panel.querySelectorAll('.tab-variante').forEach(btn => {
    btn.addEventListener('click', () => {
      panel.querySelectorAll('.tab-variante').forEach(b => {
        b.className = 'tab-variante px-2 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600';
      });
      btn.className = 'tab-variante px-2 py-1 rounded-lg text-xs font-semibold bg-optica-600 text-white';
      const texto = panel.querySelector('.variante-texto');
      if (texto) texto.textContent = personalizar(esc.cx.variantes[btn.dataset.variante] || '');
    });
  });
}

function refrescarCxPanel(card, esc) {
  const panel = card.querySelector('.cx-panel');
  if (!panel || panel.classList.contains('hidden')) return;
  panel.innerHTML = renderCxGuide(esc);
  enlazarChipsCopiar(panel);
  enlazarVariantes(card, esc);
}

async function actualizarCard(card) {
  const found = buscarEscenario(card.dataset.escenarioId);
  if (!found) return;
  const esc = found.esc;
  const { faseActiva, canalActivo } = estadoCard(card);
  const textoEl = card.querySelector('.script-texto');
  const link = card.querySelector('.link-wa');
  const loading = card.querySelector('.script-loading');

  if (canalActivo === 'voz') {
    textoEl.textContent = personalizar(esc.fases[faseActiva].voz);
    if (link) {
      link.classList.add('pointer-events-none', 'opacity-50');
      link.href = '#';
    }
  } else {
    loading?.classList.remove('hidden');
    try {
      const plantilla = esc.fases[faseActiva].whatsapp;
      const data = await armarWhatsAppCompleto(plantilla);
      textoEl.textContent = data.mensaje;
      const aviso = document.getElementById('aviso-ficha-wa');
      if (aviso) aviso.classList.toggle('hidden', !!data.incluye_ficha);
      if (link) {
        if (data.wa_link) {
          link.href = data.wa_link;
          link.classList.remove('pointer-events-none', 'opacity-50');
        } else {
          link.href = '#';
          link.classList.add('pointer-events-none', 'opacity-50');
        }
      }
    } catch (err) {
      textoEl.textContent = '❌ ' + err.message;
    } finally {
      loading?.classList.add('hidden');
    }
  }
  refrescarCxPanel(card, esc);
}

function copiarDesdeCard(cardId, btn) {
  const card = document.getElementById(cardId);
  const texto = card.querySelector('.script-texto')?.textContent || '';
  copiarTexto(texto, btn);
}
window.copiarDesdeCard = copiarDesdeCard;

function escenariosVisibles() {
  const grupos = grupoFiltro
    ? datos.grupos.filter(g => g.id === grupoFiltro)
    : datos.grupos;
  const q = val('buscar-script').toLowerCase();
  const cards = [];
  grupos.forEach(grupo => {
    grupo.escenarios.forEach(esc => {
      if (q) {
        const hay = [esc.titulo, esc.objetivo, esc.descripcion, grupo.titulo]
          .join(' ').toLowerCase().includes(q);
        if (!hay) return;
      }
      cards.push({ grupo, esc });
    });
  });
  return cards;
}

function renderGrid() {
  const items = escenariosVisibles();

  grid.innerHTML = items.length
    ? items.map(({ grupo, esc }) => cardEscenario(grupo, esc)).join('')
    : '<p class="text-slate-400 col-span-full text-center py-8">Sin scripts en este filtro</p>';

  document.querySelectorAll('.tab-fase').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = document.getElementById(btn.dataset.card);
      card.querySelectorAll('.tab-fase').forEach(b => {
        b.className = 'tab-fase px-3 py-1.5 rounded-lg text-sm font-semibold transition bg-slate-100 text-slate-600 hover:bg-slate-200';
      });
      btn.className = 'tab-fase px-3 py-1.5 rounded-lg text-sm font-semibold transition bg-optica-600 text-white';
      actualizarCard(card);
    });
  });

  document.querySelectorAll('.tab-canal').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = document.getElementById(btn.dataset.card);
      card.querySelectorAll('.tab-canal').forEach(b => {
        b.className = 'tab-canal flex-1 py-2 rounded-xl text-sm font-bold transition bg-slate-100 text-slate-600 hover:bg-slate-200';
      });
      btn.className = 'tab-canal flex-1 py-2 rounded-xl text-sm font-bold transition bg-optica-600 text-white';
      actualizarCard(card);
    });
  });

  document.querySelectorAll('.btn-toggle-cx').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = document.getElementById(btn.dataset.card);
      const panel = card.querySelector('.cx-panel');
      const abierto = !panel.classList.contains('hidden');
      panel.classList.toggle('hidden');
      btn.textContent = abierto ? '📖 Ver guía CX completa' : '📕 Ocultar guía CX';
      if (!abierto) {
        const found = buscarEscenario(card.dataset.escenarioId);
        if (found) {
          enlazarChipsCopiar(panel);
          enlazarVariantes(card, found.esc);
        }
      }
    });
  });

  items.forEach(({ esc }) => {
    const card = document.getElementById(`card-${esc.id}`);
    if (card) actualizarCard(card);
  });
}

function renderFiltros() {
  const btns = datos.grupos.map(g => `
    <button type="button" data-grupo="${g.id}"
      class="filtro-grupo shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-white hover:bg-slate-50 whitespace-nowrap">
      ${escapeHtml(g.titulo)} <span class="text-slate-400 font-normal">(${g.escenarios.length})</span>
    </button>
  `).join('');
  const total = datos.grupos.reduce((n, g) => n + g.escenarios.length, 0);
  filtroGrupos.innerHTML = btns + `
    <button type="button" data-grupo=""
      class="filtro-grupo shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-optica-600 text-white whitespace-nowrap">
      Todos (${total})
    </button>
  `;

  filtroGrupos.querySelectorAll('.filtro-grupo').forEach(btn => {
    btn.addEventListener('click', () => {
      filtroGrupos.querySelectorAll('.filtro-grupo').forEach(b => {
        b.className = 'filtro-grupo shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-white hover:bg-slate-50 whitespace-nowrap';
      });
      btn.className = 'filtro-grupo shrink-0 px-3 sm:px-4 py-2 rounded-xl text-sm font-semibold border transition bg-optica-600 text-white whitespace-nowrap';
      grupoFiltro = btn.dataset.grupo;
      actualizarCamposFechas();
      actualizarModoPosventa();
      renderGrid();
    });
  });
}

function renderFrasesCopiables(panelId, listaId, items, btnClass, labelClass, btnStyle, visible) {
  const panel = document.getElementById(panelId);
  const lista = document.getElementById(listaId);
  if (!panel || !lista) return;

  if (!visible || !items.length) {
    panel.classList.add('hidden');
    lista.innerHTML = '';
    return;
  }

  panel.classList.remove('hidden');
  lista.innerHTML = items.map(bloque => `
    <div>
      <p class="text-xs font-bold uppercase ${labelClass} mb-2">${escapeHtml(bloque.situacion)}</p>
      <div class="flex flex-wrap gap-2">
        ${(bloque.frases || []).map(frase => {
          const texto = personalizar(frase);
          return `
            <button type="button"
              class="${btnClass} ${btnStyle} text-left text-sm bg-white rounded-xl px-3 py-2 transition text-slate-700">
              ${escapeHtml(texto)}
            </button>
          `;
        }).join('')}
      </div>
    </div>
  `).join('');

  lista.querySelectorAll(`.${btnClass}`).forEach(btn => {
    btn.addEventListener('click', () => copiarTexto(btn.textContent.trim(), btn));
  });
}

function renderPalabrasCalma() {
  const grupo = grupoActivo();
  renderFrasesCopiables(
    'panel-palabras-calma',
    'lista-palabras-calma',
    esPosventa() ? (grupo?.palabras_calma || []) : [],
    'btn-calma',
    'text-violet-700',
    'border border-violet-200 hover:bg-violet-100 hover:border-violet-300',
    esPosventa(),
  );
}

function renderSituacionesRetiro() {
  const grupo = grupoActivo();
  renderFrasesCopiables(
    'panel-situaciones-retiro',
    'lista-situaciones-retiro',
    esGarantiaNoAprobada() ? (grupo?.situaciones_retiro || []) : [],
    'btn-retiro',
    'text-amber-800',
    'border border-amber-200 hover:bg-amber-100 hover:border-amber-300',
    esGarantiaNoAprobada(),
  );
}

function actualizarModoPosventa() {
  const simple = esModoSimple();
  document.getElementById('bloque-ficha-completa')?.classList.toggle('hidden', simple);
  document.getElementById('campos-ficha-extended')?.classList.toggle('hidden', simple);
  document.getElementById('bloque-respuesta-ia')?.classList.toggle('hidden', simple);
  document.getElementById('aviso-ficha-wa')?.classList.toggle('hidden', simple);

  const titulo = document.getElementById('titulo-datos-ficha');
  const desc = document.getElementById('desc-datos-ficha');
  if (titulo) {
    if (esPosventa()) titulo.textContent = '📞 Datos de la llamada';
    else if (esGarantiaNoAprobada()) titulo.textContent = '📞 Datos de la comunicación';
    else titulo.textContent = '📋 Datos de la ficha';
  }
  if (desc) {
    if (esPosventa()) {
      desc.textContent = 'Solo necesita el nombre del asesor y del cliente. Llamada breve de experiencia — escuche con empatía, sin indagar de más.';
    } else if (esGarantiaNoAprobada()) {
      desc.textContent = 'Solo asesor y cliente. Informe con respeto que la garantía no fue aprobada e indique que puede retirar su compra en la tienda.';
    } else {
      desc.textContent = 'Complete manualmente o cargue desde Atención/Historial. La ficha en WhatsApp solo aparece cuando hay datos reales del cliente (nombre + tienda o factura).';
    }
  }

  renderPalabrasCalma();
  renderSituacionesRetiro();
}

function actualizarCamposFechas() {
  const grupo = grupoActivo();
  const mostrar = grupoFiltro === 'situaciones_operativas'
    || grupoFiltro === ''
    || grupo?.escenarios?.some(e => e.requiere_fechas);
  ['campo-fecha-prometida', 'campo-nueva-fecha', 'campo-motivo'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !mostrar);
  });
}

function actualizarTodos() {
  document.querySelectorAll('[id^="card-"]').forEach(actualizarCard);
}

function aplicarFichaAlFormulario(ficha) {
  fichaCargada = ficha;
  document.getElementById('var-cliente').value = ficha.nombre || '';
  document.getElementById('var-cedula').value = ficha.cedula || '';
  document.getElementById('var-telefono').value = ficha.telefono || '';
  document.getElementById('var-producto').value = ficha.producto || '';
  document.getElementById('var-factura').value = ficha.numero_factura || '';
  document.getElementById('var-fecha-factura').value = ficha.fecha_factura || '';

  const selTipo = document.getElementById('var-tipo-producto');
  if (ficha.tipo_producto) {
    const opt = [...selTipo.options].find(o => o.value === ficha.tipo_producto);
    selTipo.value = opt ? ficha.tipo_producto : '';
  }

  const selTienda = document.getElementById('var-tienda');
  const tid = tiendaIdPorNombre(ficha.tienda);
  if (tid) selTienda.value = tid;

  const origen = document.getElementById('ficha-origen');
  const fuenteLabel = ficha.fuente === 'historial'
    ? `Historial #${ficha.historial_id}`
    : ficha.fuente === 'atencion'
      ? `Atención #${ficha.id}`
      : 'Manual';
  let extra = '';
  if (ficha.veredicto) extra += ` · Veredicto: ${ficha.veredicto}`;
  if (ficha.estado_garantia) extra += ` · ${ficha.estado_garantia}`;
  origen.textContent = `✅ Ficha cargada desde ${fuenteLabel}${extra}`;
  origen.classList.remove('hidden');

  actualizarTodos();
  document.getElementById('aviso-ficha-wa')?.classList.add('hidden');
}

async function cargarFicha(tipo, id) {
  const url = tipo === 'atencion'
    ? `/api/scripts/ficha/atencion/${id}`
    : `/api/scripts/ficha/historial/${id}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'No se pudo cargar la ficha');
  aplicarFichaAlFormulario(data);
  document.getElementById('resultados-ficha').innerHTML = '';
}

async function buscarFichas() {
  const q = val('buscar-ficha');
  const cont = document.getElementById('resultados-ficha');
  if (q.length < 2) {
    cont.innerHTML = '<p class="text-sm text-amber-600">Escriba al menos 2 caracteres.</p>';
    return;
  }
  cont.innerHTML = '<p class="text-sm text-slate-400">Buscando...</p>';
  try {
    const res = await fetch(`/api/scripts/buscar?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.resultados?.length) {
      cont.innerHTML = '<p class="text-sm text-slate-400">Sin resultados.</p>';
      return;
    }
    cont.innerHTML = data.resultados.map(r => `
      <button type="button" data-tipo="${r.tipo}" data-id="${r.id}"
        class="w-full text-left bg-white border rounded-xl px-4 py-3 hover:bg-optica-50 hover:border-optica-200 transition">
        <span class="text-xs font-bold uppercase ${r.tipo === 'atencion' ? 'text-optica-600' : 'text-purple-600'}">
          ${r.tipo === 'atencion' ? '👥 Atención' : '📋 Historial'}
        </span>
        <p class="font-semibold text-slate-800">${escapeHtml(r.titulo)}</p>
        <p class="text-xs text-slate-500">${escapeHtml(r.subtitulo)}</p>
      </button>
    `).join('');

    cont.querySelectorAll('button[data-tipo]').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await cargarFicha(btn.dataset.tipo, btn.dataset.id);
        } catch (err) {
          alert(err.message);
        }
      });
    });
  } catch {
    cont.innerHTML = '<p class="text-sm text-red-500">Error al buscar.</p>';
  }
}

async function generarRespuesta() {
  const mensaje = val('mensaje-cliente');
  const status = document.getElementById('respuesta-status');
  const btn = document.getElementById('btn-generar-respuesta');

  if (mensaje.length < 2) {
    status.textContent = '⚠️ Escriba el mensaje del cliente.';
    status.className = 'text-sm text-amber-600';
    return;
  }
  if (!val('var-cliente')) {
    status.textContent = '⚠️ Cargue o complete la ficha del cliente primero.';
    status.className = 'text-sm text-amber-600';
    return;
  }

  btn.disabled = true;
  status.textContent = '⏳ Generando respuesta...';
  status.className = 'text-sm text-slate-500';

  try {
    const res = await fetch('/api/scripts/generar-respuesta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mensaje_cliente: mensaje,
        asesor: val('var-asesor'),
        ficha: construirFichaDesdeFormulario(),
        escenario: grupoFiltro || 'general',
        contexto_adicional: val('contexto-respuesta'),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al generar');

    document.getElementById('respuesta-voz').textContent = data.mensaje_voz;
    document.getElementById('respuesta-whatsapp').textContent = data.mensaje_whatsapp;
    ultimoWaMensaje = data.mensaje_whatsapp;
    ultimoWaLink = data.wa_link || '';

    const link = document.getElementById('link-respuesta-wa');
    if (ultimoWaLink) {
      link.href = ultimoWaLink;
      link.classList.remove('pointer-events-none', 'opacity-50');
    } else {
      link.href = '#';
      link.classList.add('pointer-events-none', 'opacity-50');
    }

    const por = data.generado_por === 'ia' ? 'IA' : 'plantilla';
    status.textContent = `✅ Respuesta generada (${por}). Lista para enviar por WhatsApp.`;
    status.className = 'text-sm text-emerald-600 font-medium';
  } catch (err) {
    status.textContent = '❌ ' + err.message;
    status.className = 'text-sm text-red-600';
  } finally {
    btn.disabled = false;
  }
}

function initTiendas() {
  const sel = document.getElementById('var-tienda');
  TIENDAS.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = `${t.nombre} (${t.ciudad})`;
    sel.appendChild(opt);
  });
}

async function cargarScripts() {
  const res = await fetch('/api/scripts');
  datos = await res.json();
  const badge = document.getElementById('cx-version-badge');
  if (badge && datos.marco) {
    badge.textContent = `${datos.marco} · ${datos.grupos.reduce((n, g) => n + g.escenarios.length, 0)} scripts`;
  }
  renderFiltros();
  actualizarModoPosventa();
  renderGrid();
}

const CAMPOS = [
  'var-asesor', 'var-cliente', 'var-cedula', 'var-telefono', 'var-tienda',
  'var-producto', 'var-tipo-producto', 'var-factura', 'var-fecha-factura',
  'var-fecha-prometida', 'var-nueva-fecha', 'var-motivo',
];
function onCampoChange() {
  actualizarTodos();
  if (esPosventa()) renderPalabrasCalma();
  if (esGarantiaNoAprobada()) renderSituacionesRetiro();
}

CAMPOS.forEach(id => {
  document.getElementById(id)?.addEventListener('input', onCampoChange);
  document.getElementById(id)?.addEventListener('change', onCampoChange);
});

document.getElementById('btn-buscar-ficha')?.addEventListener('click', buscarFichas);
document.getElementById('buscar-ficha')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') buscarFichas();
});
document.getElementById('buscar-script')?.addEventListener('input', renderGrid);
document.getElementById('btn-generar-respuesta')?.addEventListener('click', generarRespuesta);
document.getElementById('btn-copiar-respuesta-wa')?.addEventListener('click', function () {
  if (ultimoWaMensaje) copiarTexto(ultimoWaMensaje, this);
});

initTiendas();
cargarScripts();