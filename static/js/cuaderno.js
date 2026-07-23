/**
 * Cuaderno creativo — notas + imágenes en BD
 */

let notasCache = [];
let categorias = [];
let catActiva = "";
let notaActualId = null;

function toast(msg, tipo = "info") {
  const el = document.getElementById("toast-cuaderno");
  if (!el) return;
  el.textContent = msg;
  el.className = `fixed bottom-4 right-4 z-50 glass-card px-4 py-3 text-sm font-medium shadow-lg toast-${tipo}`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3500);
}

function escapeHtml(t) {
  const d = document.createElement("div");
  d.textContent = t ?? "";
  return d.innerHTML;
}

async function cargarNotas() {
  const q = document.getElementById("cuaderno-buscar")?.value?.trim() || "";
  const fijadas = document.getElementById("cuaderno-fijadas")?.checked || false;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (catActiva) params.set("categoria", catActiva);
  if (fijadas) params.set("fijadas", "true");
  const res = await fetch(`/api/cuaderno?${params}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Error al cargar");
  notasCache = data.notas || [];
  categorias = data.categorias || [];
  renderCats();
  renderGrid();
  fillCategoriaSelect();
}

function renderCats() {
  const el = document.getElementById("cuaderno-cats");
  if (!el) return;
  const all = [{ id: "", label: "Todas", emoji: "📚" }, ...categorias];
  el.innerHTML = all
    .map(
      (c) =>
        `<button type="button" class="cuaderno-chip ${catActiva === c.id ? "is-on" : ""}" data-cat="${escapeHtml(c.id)}">${escapeHtml(c.emoji || "")} ${escapeHtml(c.label)}</button>`
    )
    .join("");
  el.querySelectorAll("[data-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      catActiva = btn.getAttribute("data-cat") || "";
      cargarNotas().catch((e) => toast(e.message, "error"));
    });
  });
}

function fillCategoriaSelect() {
  const sel = document.getElementById("nota-categoria");
  if (!sel || !categorias.length) return;
  const cur = sel.value;
  sel.innerHTML = categorias
    .map((c) => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.emoji)} ${escapeHtml(c.label)}</option>`)
    .join("");
  if (cur) sel.value = cur;
}

function renderGrid() {
  const grid = document.getElementById("cuaderno-grid");
  if (!grid) return;
  if (!notasCache.length) {
    grid.innerHTML = `
      <div class="cuaderno-empty">
        <p class="text-4xl mb-2">📔</p>
        <p class="font-semibold text-slate-600">Tu cuaderno está vacío</p>
        <p class="text-sm mt-1">Crea la primera anotación para guardar ideas, órdenes, acuerdos e imágenes.</p>
      </div>`;
    return;
  }
  grid.innerHTML = notasCache
    .map((n) => {
      const tags = (n.tags || []).slice(0, 4)
        .map((t) => `<span class="nota-card__tag">#${escapeHtml(t)}</span>`)
        .join("");
      const thumbs = (n.adjuntos || [])
        .slice(0, 3)
        .map((a) => `<img src="${escapeHtml(a.url)}" alt="">`)
        .join("");
      const body = (n.contenido || "").trim() || "Sin contenido…";
      const fecha = (n.updated_at || n.created_at || "").slice(0, 16).replace("T", " ");
      return `
        <article class="nota-card c-${escapeHtml(n.color || "amber")} ${n.fijada ? "is-fijada" : ""}" data-id="${n.id}">
          <div class="nota-card__emoji">${escapeHtml(n.emoji || "📝")}</div>
          <h3 class="nota-card__titulo">${escapeHtml(n.titulo)}</h3>
          <div class="nota-card__body">${escapeHtml(body)}</div>
          ${thumbs ? `<div class="nota-card__thumbs">${thumbs}</div>` : ""}
          <div class="nota-card__meta">
            <span>${escapeHtml(n.categoria)}</span>
            ${tags}
            <span class="ml-auto">${escapeHtml(fecha)}</span>
          </div>
        </article>`;
    })
    .join("");
  grid.querySelectorAll(".nota-card").forEach((card) => {
    card.addEventListener("click", () => abrirNota(Number(card.dataset.id)));
  });
}

function abrirModalNueva() {
  notaActualId = null;
  document.getElementById("modal-nota-titulo-ui").textContent = "Nueva anotación";
  document.getElementById("nota-id").value = "";
  document.getElementById("nota-titulo").value = "";
  document.getElementById("nota-contenido").value = "";
  document.getElementById("nota-tags").value = "";
  document.getElementById("nota-fijada").checked = false;
  document.getElementById("nota-autor").value = window.DEFAULT_ASESOR || "";
  document.getElementById("nota-emoji").value = "📝";
  document.getElementById("nota-color").value = "amber";
  document.getElementById("btn-eliminar-nota").classList.add("hidden");
  document.getElementById("nota-galeria").innerHTML = "";
  setPick("nota-emoji-pick", "📝");
  setPickColor("amber");
  fillCategoriaSelect();
  document.getElementById("modal-nota").classList.remove("hidden");
}

function setPick(rowId, value) {
  document.querySelectorAll(`#${rowId} button`).forEach((b) => {
    b.classList.toggle("is-on", b.dataset.e === value);
  });
}

function setPickColor(color) {
  document.querySelectorAll("#nota-color-pick button").forEach((b) => {
    b.classList.toggle("is-on", b.dataset.c === color);
  });
}

async function abrirNota(id) {
  const res = await fetch(`/api/cuaderno/${id}`);
  const n = await res.json();
  if (!res.ok) throw new Error(n.detail || "No encontrada");
  notaActualId = id;
  document.getElementById("modal-nota-titulo-ui").textContent = "Editar anotación";
  document.getElementById("nota-id").value = String(id);
  document.getElementById("nota-titulo").value = n.titulo || "";
  document.getElementById("nota-contenido").value = n.contenido || "";
  document.getElementById("nota-tags").value = (n.tags || []).join(", ");
  document.getElementById("nota-fijada").checked = !!n.fijada;
  document.getElementById("nota-autor").value = n.autor || window.DEFAULT_ASESOR || "";
  document.getElementById("nota-emoji").value = n.emoji || "📝";
  document.getElementById("nota-color").value = n.color || "amber";
  fillCategoriaSelect();
  document.getElementById("nota-categoria").value = n.categoria || "general";
  setPick("nota-emoji-pick", n.emoji || "📝");
  setPickColor(n.color || "amber");
  renderGaleria(n.adjuntos || []);
  document.getElementById("btn-eliminar-nota").classList.remove("hidden");
  document.getElementById("modal-nota").classList.remove("hidden");
}

function renderGaleria(adjuntos) {
  const g = document.getElementById("nota-galeria");
  if (!g) return;
  if (!adjuntos.length) {
    g.innerHTML = "";
    return;
  }
  g.innerHTML = adjuntos
    .map(
      (a) => `
    <div class="thumb">
      <img src="${escapeHtml(a.url)}" alt="${escapeHtml(a.nombre || "")}">
      <button type="button" data-del-adj="${a.id}" title="Quitar">✕</button>
    </div>`
    )
    .join("");
  g.querySelectorAll("[data-del-adj]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-del-adj");
      if (!confirm("¿Quitar esta imagen?")) return;
      const res = await fetch(`/api/cuaderno/adjuntos/${id}`, { method: "DELETE" });
      if (!res.ok) {
        toast("No se pudo eliminar", "error");
        return;
      }
      if (notaActualId) await abrirNota(notaActualId);
      await cargarNotas();
    });
  });
}

async function guardarNota() {
  const payload = {
    titulo: document.getElementById("nota-titulo").value.trim() || "Sin título",
    contenido: document.getElementById("nota-contenido").value,
    emoji: document.getElementById("nota-emoji").value || "📝",
    color: document.getElementById("nota-color").value || "amber",
    categoria: document.getElementById("nota-categoria").value || "general",
    tags: document.getElementById("nota-tags").value,
    fijada: document.getElementById("nota-fijada").checked,
    autor: document.getElementById("nota-autor").value.trim() || window.DEFAULT_ASESOR || "",
  };
  const id = document.getElementById("nota-id").value;
  let res;
  if (id) {
    res = await fetch(`/api/cuaderno/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    res = await fetch("/api/cuaderno", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Error al guardar");
  notaActualId = data.id;
  document.getElementById("nota-id").value = String(data.id);
  document.getElementById("btn-eliminar-nota").classList.remove("hidden");
  toast("💾 Guardado en base de datos", "ok");
  await cargarNotas();
  await cargarActividad();
}

async function eliminarNota() {
  const id = document.getElementById("nota-id").value;
  if (!id || !confirm("¿Eliminar esta anotación y sus imágenes?")) return;
  const res = await fetch(`/api/cuaderno/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("No se pudo eliminar");
  document.getElementById("modal-nota").classList.add("hidden");
  toast("Nota eliminada", "ok");
  await cargarNotas();
  await cargarActividad();
}

async function subirImagen(file) {
  if (!file) return;
  let id = document.getElementById("nota-id").value;
  if (!id) {
    await guardarNota();
    id = document.getElementById("nota-id").value;
  }
  if (!id) return;
  const fd = new FormData();
  fd.append("archivo", file);
  const res = await fetch(`/api/cuaderno/${id}/imagen`, { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Error al subir imagen");
  renderGaleria(data.adjuntos || []);
  toast("🖼️ Imagen agregada", "ok");
  await cargarNotas();
}

async function cargarActividad() {
  const el = document.getElementById("cuaderno-actividad");
  if (!el) return;
  try {
    const res = await fetch("/api/actividad?limit=30");
    const data = await res.json();
    const items = data.items || [];
    if (!items.length) {
      el.innerHTML = "Aún no hay actividad registrada.";
      return;
    }
    el.innerHTML = items
      .map((i) => {
        const t = (i.created_at || "").replace("T", " ").slice(0, 16);
        return `<div><strong>${escapeHtml(i.modulo)}</strong> · ${escapeHtml(i.accion)} — ${escapeHtml(i.detalle || "")} <span class="text-slate-400">${escapeHtml(t)}</span></div>`;
      })
      .join("");
  } catch {
    el.textContent = "No se pudo cargar actividad.";
  }
}

// picks
document.getElementById("nota-emoji-pick")?.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-e]");
  if (!b) return;
  document.getElementById("nota-emoji").value = b.dataset.e;
  setPick("nota-emoji-pick", b.dataset.e);
});
document.getElementById("nota-color-pick")?.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-c]");
  if (!b) return;
  document.getElementById("nota-color").value = b.dataset.c;
  setPickColor(b.dataset.c);
});

document.getElementById("btn-nueva-nota")?.addEventListener("click", abrirModalNueva);
document.getElementById("modal-nota-cerrar")?.addEventListener("click", () =>
  document.getElementById("modal-nota").classList.add("hidden"));
document.getElementById("btn-guardar-nota")?.addEventListener("click", () =>
  guardarNota().catch((e) => toast(e.message, "error")));
document.getElementById("btn-eliminar-nota")?.addEventListener("click", () =>
  eliminarNota().catch((e) => toast(e.message, "error")));
document.getElementById("nota-imagen")?.addEventListener("change", (e) => {
  const f = e.target.files?.[0];
  if (f) subirImagen(f).catch((err) => toast(err.message, "error"));
  e.target.value = "";
});
document.getElementById("cuaderno-buscar")?.addEventListener("input", () => {
  clearTimeout(window._cuadernoDeb);
  window._cuadernoDeb = setTimeout(() => cargarNotas().catch((e) => toast(e.message, "error")), 300);
});
document.getElementById("cuaderno-fijadas")?.addEventListener("change", () =>
  cargarNotas().catch((e) => toast(e.message, "error")));
document.getElementById("btn-refrescar-act")?.addEventListener("click", () =>
  cargarActividad());

cargarNotas().catch((e) => toast(e.message, "error"));
cargarActividad();
