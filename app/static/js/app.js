// Marmarula — JS sin dependencias. Sin innerHTML con datos: todo se pinta con
// textContent/atributos para evitar XSS. El carrito vive en localStorage y los
// precios se recalculan SIEMPRE en el servidor (/api/v1/cart/quote).
"use strict";

const CART_KEY = "marmarula:cart:v1";
const MAX_QTY = 20;

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
  const res = await fetch("/api/v1/cart/quote", {
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
      img.src = `${line.image}?w=200&q=70&auto=format&fit=crop`;
      const name = node.querySelector(".line__name");
      name.textContent = line.name;
      name.href = `/p/${encodeURIComponent(line.product_id)}`;
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
  initCartPage();
});
window.addEventListener("storage", updateBadges);
