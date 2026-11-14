// Marmarula — JS sin dependencias. Sin innerHTML con datos: todo se pinta con
// textContent/atributos para evitar XSS. El carrito vive en localStorage.
// - Con servidor (FastAPI): los precios se recalculan en /api/v1/cart/quote.
// - Versión estática (GitHub Pages): se calculan aquí con el catálogo publicado
//   y la tienda confirma el pedido final por WhatsApp.
"use strict";

const CART_KEY = "marmarula:cart:v1";
const MAX_QTY = 20;
const BASE = document.body.dataset.base || "";
const STATIC = document.body.dataset.static === "true";

const money = (n) => "$ " + n.toLocaleString("es-CO");

const Cart = {
  read() {
    try {
      const data = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
      return Array.isArray(data) ? data.filter((i) => i && typeof i.id === "string") : [];
    } catch {
      return [];
    }
  },
  write(items) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(items));
    } catch {
      /* almacenamiento bloqueado: el carrito funciona solo en esta vista */
    }
    updateBadges();
  },
  add(id, variant, qty) {
    const items = Cart.read();
    const found = items.find((i) => i.id === id && i.variant === variant);
    if (found) found.qty = Math.min(found.qty + qty, MAX_QTY);
    else items.push({ id, variant, qty: Math.min(qty, MAX_QTY) });
    Cart.write(items);
  },
  count() {
    return Cart.read().reduce((sum, i) => sum + (Number(i.qty) || 0), 0);
  },
};

function updateBadges() {
  const n = Cart.count();
  document.querySelectorAll("[data-cart-count]").forEach((el) => {
    el.textContent = String(n);
    el.hidden = n === 0;
  });
}

let toastTimer;
function toast(message) {
  const el = document.querySelector("[data-toast]");
  if (!el) return;
  el.textContent = message;
  el.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("is-visible"), 2200);
}

// ---------- Detalle de producto ----------
function initProductPage() {
  const root = document.querySelector("[data-product]");
  if (!root) return;
  const output = document.querySelector("[data-qty-value]");
  const total = document.querySelector("[data-buy-total]");
  const addBtn = document.querySelector("[data-add-to-cart]");
  const unit = Number(total?.dataset.unit || 0);
  const max = Math.min(Number(addBtn?.dataset.max || MAX_QTY), MAX_QTY);
  let qty = 1;

  document.querySelectorAll("[data-qty]").forEach((btn) =>
    btn.addEventListener("click", () => {
      qty = Math.max(1, Math.min(max, qty + Number(btn.dataset.qty)));
      output.textContent = String(qty);
      if (total) total.textContent = money(unit * qty);
    })
  );

  const currentVariant = () => {
    const selected = root.querySelector('input[name="variant"]:checked');
    return root.dataset.hasVariants === "true" ? selected?.value ?? null : null;
  };

  addBtn?.addEventListener("click", () => {
    Cart.add(root.dataset.product, currentVariant(), qty);
    toast(`✓ ${root.dataset.name} agregado al carrito`);
  });

  // "Comprar ahora": cotiza solo este producto y abre WhatsApp con el pedido listo.
  const buyNow = document.querySelector("[data-buy-now]");
  buyNow?.addEventListener("click", async () => {
    buyNow.disabled = true;
    try {
      const quote = await requestQuote([{ id: root.dataset.product, variant: currentVariant(), qty }]);
      window.location.href = quote.whatsapp_url;
    } catch (err) {
      toast(err.message);
    } finally {
      buyNow.disabled = false;
    }
  });
}

// ---------- Galería de fotos ----------
function initGallery() {
  const gallery = document.querySelector("[data-gallery]");
  const track = gallery?.querySelector("[data-gallery-track]");
  if (!track) return;
  const counter = gallery.querySelector("[data-gallery-count]");
  const thumbs = [...gallery.querySelectorAll("[data-gallery-go]")];
  const total = track.children.length;

  const current = () => Math.round(track.scrollLeft / track.clientWidth);
  const show = (i) => {
    if (counter) counter.textContent = `${i + 1} / ${total}`;
    thumbs.forEach((t, n) => t.classList.toggle("is-active", n === i));
  };
  track.addEventListener("scroll", () => show(current()), { passive: true });
  thumbs.forEach((t) =>
    t.addEventListener("click", () =>
      track.scrollTo({ left: Number(t.dataset.galleryGo) * track.clientWidth, behavior: "smooth" })
    )
  );
  track.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = Math.max(0, Math.min(total - 1, current() + (e.key === "ArrowRight" ? 1 : -1)));
    track.scrollTo({ left: next * track.clientWidth, behavior: "smooth" });
  });
}

async function requestQuote(items) {
  if (STATIC) return localQuote(items);
  const res = await fetch(`${BASE}/api/v1/cart/quote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      items: items.map((i) => ({ product_id: i.id, variant: i.variant, quantity: i.qty })),
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Revisa tu carrito");
  return data;
}

// ---------- Versión estática: catálogo y cálculo en el navegador ----------
let catalogPromise;
function loadCatalog() {
  catalogPromise ??= fetch(`${BASE}/api/catalog.json`).then((r) => {
    if (!r.ok) throw new Error("No se pudo cargar el catálogo");
    return r.json();
  });
  return catalogPromise;
}

// Misma lógica y mismos mensajes que app/cart.py (build_quote).
async function localQuote(items) {
  const { settings, products } = await loadCatalog();
  const byId = new Map(products.map((p) => [p.id, p]));
  const merged = new Map();
  for (const i of items) {
    const key = JSON.stringify([i.id, i.variant ?? null]);
    merged.set(key, (merged.get(key) || 0) + Number(i.qty));
  }
  const lines = [];
  for (const [key, quantity] of merged) {
    const [id, variant] = JSON.parse(key);
    const p = byId.get(id);
    if (!p) throw new Error(`El producto '${id}' no existe`);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QTY) throw new Error("Cantidad no válida");
    if (p.variants.length && !p.variants.includes(variant)) throw new Error(`Elige una opción válida para '${p.name}'`);
    if (!p.variants.length && variant !== null) throw new Error(`'${p.name}' no tiene opciones`);
    if (quantity > p.stock) throw new Error(`Solo quedan ${p.stock} unidades de '${p.name}'`);
    lines.push({
      product_id: p.id, name: p.name, image: p.image, variant, quantity,
      unit_price: p.price, line_total: p.price * quantity,
    });
  }
  const subtotal = lines.reduce((s, l) => s + l.line_total, 0);
  const remaining = Math.max(settings.free_shipping_threshold - subtotal, 0);
  const free = remaining === 0;
  const rows = [`¡Hola ${settings.app_name}! 🌸 Quiero hacer este pedido:`, ""];
  for (const l of lines) {
    rows.push(`• ${l.quantity} x ${l.name}${l.variant ? ` (${l.variant})` : ""} — ${money(l.line_total)}`);
  }
  rows.push("", `Subtotal: ${money(subtotal)} ${settings.currency}`, `Envío: ${free ? "GRATIS 🎉" : "por confirmar"}`);
  return {
    lines,
    item_count: lines.reduce((s, l) => s + l.quantity, 0),
    subtotal,
    currency: settings.currency,
    free_shipping: free,
    free_shipping_threshold: settings.free_shipping_threshold,
    free_shipping_remaining: remaining,
    whatsapp_url: `https://wa.me/${settings.whatsapp_number}?text=${encodeURIComponent(rows.join("\n"))}`,
  };
}

function unsplash(url, width) {
  if (!url.startsWith("https://images.unsplash.com/")) return url;
  return `${url}${url.includes("?") ? "&" : "?"}w=${width}&q=75&auto=format&fit=crop`;
}

// Búsqueda (versión estática): mismos criterios que CatalogRepository.search.
async function initStaticSearch() {
  const results = document.querySelector("[data-search-results]");
  if (!STATIC || !results) return;
  const q = (new URLSearchParams(location.search).get("q") || "").trim().slice(0, 60);
  if (!q) return;
  document.getElementById("q").value = q;
  document.querySelector("[data-search-suggestions]")?.setAttribute("hidden", "");
  const terms = q.toLowerCase().split(/\s+/);
  const { products } = await loadCatalog();
  const found = products.filter((p) => {
    const hay = `${p.name} ${p.description} ${p.category} ${p.variants.join(" ")}`.toLowerCase();
    return terms.every((t) => hay.includes(t));
  });
  const count = document.querySelector("[data-search-count]");
  count.textContent = `${found.length} resultado${found.length === 1 ? "" : "s"} para “${q}”`;
  count.hidden = false;
  const tpl = document.getElementById("card-tpl");
  for (const p of found) {
    const card = tpl.content.firstElementChild.cloneNode(true);
    card.href = `${BASE}/p/${encodeURIComponent(p.id)}`;
    if (p.stock === 0) card.classList.add("is-soldout");
    const img = card.querySelector("img");
    img.src = unsplash(p.image, 500);
    img.alt = p.name;
    const pill = card.querySelector(".pill");
    const onSale = p.compare_at_price && p.compare_at_price > p.price;
    if (p.stock === 0) { pill.textContent = "Agotado"; pill.classList.add("pill--dark"); pill.hidden = false; }
    else if (onSale) { pill.textContent = `-${Math.round((1 - p.price / p.compare_at_price) * 100)}%`; pill.classList.add("pill--sale"); pill.hidden = false; }
    else if (p.badge) { pill.textContent = p.badge; pill.hidden = false; }
    card.querySelector(".card__title").textContent = p.name;
    card.querySelector(".card__price span").textContent = money(p.price);
    if (onSale) { const s = card.querySelector("s"); s.textContent = money(p.compare_at_price); s.hidden = false; }
    results.append(card);
  }
  if (!found.length) {
    const msg = document.createElement("p");
    msg.className = "empty";
    msg.textContent = "No encontramos nada. Prueba con otra palabra.";
    results.append(msg);
  }
}

// Orden por precio (versión estática): reordena las tarjetas ya pintadas.
function initStaticSort() {
  const grid = document.querySelector("[data-sort-grid]");
  if (!STATIC || !grid) return;
  const sort = new URLSearchParams(location.search).get("sort") || "destacados";
  const select = document.getElementById("sort");
  if (select && [...select.options].some((o) => o.value === sort)) select.value = sort;
  const cards = [...grid.children];
  const price = (c) => Number(c.dataset.price);
  if (sort === "precio-asc") cards.sort((a, b) => price(a) - price(b));
  else if (sort === "precio-desc") cards.sort((a, b) => price(b) - price(a));
  else cards.sort((a, b) => Number(b.dataset.featured) - Number(a.dataset.featured));
  grid.append(...cards);
}

// ---------- Carrito ----------
async function initCartPage() {
  const root = document.querySelector("[data-cart-root]");
  if (!root) return;
  const list = root.querySelector("[data-cart-list]");
  const empty = root.querySelector("[data-cart-empty]");
  const totals = root.querySelector("[data-cart-totals]");
  const errorBox = root.querySelector("[data-cart-error]");
  const summary = document.querySelector("[data-cart-summary]");
  const tpl = document.getElementById("cart-line");

  const render = async () => {
    const items = Cart.read();
    errorBox.hidden = true;
    list.replaceChildren();

    if (items.length === 0) {
      empty.hidden = false;
      totals.hidden = true;
      summary.textContent = "0 productos";
      return;
    }
    empty.hidden = true;

    let quote;
    try {
      quote = await requestQuote(items);
    } catch (err) {
      errorBox.textContent = `${err.message}. Ajusta las cantidades o vacía el carrito.`;
      errorBox.hidden = false;
      totals.hidden = true;
      summary.textContent = "";
      const reset = document.createElement("button");
      reset.className = "btn btn--small";
      reset.type = "button";
      reset.textContent = "Vaciar carrito";
      reset.addEventListener("click", () => { Cart.write([]); render(); });
      errorBox.append(" ", reset);
      return;
    }

    for (const line of quote.lines) {
      const node = tpl.content.firstElementChild.cloneNode(true);
      const img = node.querySelector(".line__img");
      img.src = unsplash(line.image, 200);
      const name = node.querySelector(".line__name");
      name.textContent = line.name;
      name.href = `${BASE}/p/${encodeURIComponent(line.product_id)}`;
      node.querySelector(".line__variant").textContent = line.variant ?? "";
      node.querySelector(".line__price").textContent = money(line.line_total);
      node.querySelector(".line__qty").textContent = String(line.quantity);

      const change = (delta) => {
        const all = Cart.read();
        const it = all.find((i) => i.id === line.product_id && i.variant === line.variant);
        if (!it) return;
        it.qty = Math.min(MAX_QTY, it.qty + delta);
        Cart.write(it.qty > 0 ? all : all.filter((i) => i !== it));
        render();
      };
      node.querySelectorAll("[data-line-qty]").forEach((b) =>
        b.addEventListener("click", () => change(Number(b.dataset.lineQty)))
      );
      node.querySelector("[data-line-remove]").addEventListener("click", () => change(-MAX_QTY));
      list.append(node);
    }

    summary.textContent = `${quote.item_count} producto${quote.item_count === 1 ? "" : "s"}`;
    root.querySelector("[data-cart-subtotal]").textContent = `${money(quote.subtotal)} ${quote.currency}`;
    root.querySelector("[data-cart-checkout]").href = quote.whatsapp_url;
    root.querySelector("[data-cart-shipping]").textContent = quote.free_shipping ? "GRATIS" : "Por confirmar";
    const pct = quote.free_shipping_threshold
      ? Math.min(100, Math.round((quote.subtotal / quote.free_shipping_threshold) * 100))
      : 100;
    root.querySelector("[data-shipbar-fill]").style.width = `${pct}%`;
    root.querySelector("[data-shipbar-track]").setAttribute("aria-valuenow", String(pct));
    root.querySelector("[data-shipbar]").classList.toggle("is-done", quote.free_shipping);
    root.querySelector("[data-shipbar-text]").textContent = quote.free_shipping
      ? "🎉 ¡Tu pedido tiene envío GRATIS!"
      : `Te faltan ${money(quote.free_shipping_remaining)} para tener envío GRATIS`;
    totals.hidden = false;
  };

  await render();
}

// ---------- Utilidades ----------
function initAutoSubmit() {
  document.querySelectorAll("[data-autosubmit]").forEach((el) =>
    el.addEventListener("change", () => el.form?.submit())
  );
}

document.addEventListener("DOMContentLoaded", () => {
  updateBadges();
  initAutoSubmit();
  initProductPage();
  initGallery();
  initStaticSort();
  initStaticSearch();
  initCartPage();
});
window.addEventListener("storage", updateBadges);
