"""Lógica del carrito. Los precios SIEMPRE se calculan en el servidor:
el navegador solo envía ids y cantidades, nunca precios."""

from urllib.parse import quote

from app.models import CartIn, CartLine, CartQuote
from app.repository import CatalogRepository


class CartError(ValueError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def format_money(value: int) -> str:
    """45000 -> '$ 45.000'"""
    return "$ " + f"{value:,}".replace(",", ".")


def build_quote(
    cart: CartIn,
    repo: CatalogRepository,
    *,
    currency: str,
    whatsapp_number: str,
    store_name: str,
) -> CartQuote:
    merged: dict[tuple[str, str | None], int] = {}
    for item in cart.items:
        key = (item.product_id, item.variant)
        merged[key] = merged.get(key, 0) + item.quantity

    lines: list[CartLine] = []
    for (product_id, variant), quantity in merged.items():
        product = repo.product(product_id)
        if product is None:
            raise CartError(f"El producto '{product_id}' no existe")
        if product.variants and variant not in product.variants:
            raise CartError(f"Elige una opción válida para '{product.name}'")
        if not product.variants and variant is not None:
            raise CartError(f"'{product.name}' no tiene opciones")
        if quantity > product.stock:
            raise CartError(
                f"Solo quedan {product.stock} unidades de '{product.name}'", status_code=409
            )
        lines.append(
            CartLine(
                product_id=product.id,
                name=product.name,
                image=product.image,
                variant=variant,
                quantity=quantity,
                unit_price=product.price,
                line_total=product.price * quantity,
            )
        )

    subtotal = sum(line.line_total for line in lines)
    message = _whatsapp_message(lines, subtotal, currency, store_name)
    return CartQuote(
        lines=lines,
        item_count=sum(line.quantity for line in lines),
        subtotal=subtotal,
        currency=currency,
        whatsapp_url=f"https://wa.me/{whatsapp_number}?text={quote(message)}",
    )


def _whatsapp_message(lines: list[CartLine], subtotal: int, currency: str, store: str) -> str:
    rows = [f"¡Hola {store}! 🌸 Quiero hacer este pedido:", ""]
    for line in lines:
        variant = f" ({line.variant})" if line.variant else ""
        rows.append(f"• {line.quantity} x {line.name}{variant} — {format_money(line.line_total)}")
    rows += ["", f"Total: {format_money(subtotal)} {currency}"]
    return "\n".join(rows)
