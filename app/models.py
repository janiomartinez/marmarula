"""Esquemas de datos (Pydantic). Validan todo lo que entra y sale de la API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CategorySlug = Literal["accesorios", "velas", "ropa"]
PRODUCT_ID_PATTERN = r"^[a-z0-9-]{3,60}$"


class Category(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: CategorySlug
    name: str
    tagline: str
    image: str


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=PRODUCT_ID_PATTERN)
    name: str = Field(min_length=2, max_length=80)
    category: CategorySlug
    price: int = Field(gt=0, description="Precio en la moneda de la tienda, sin decimales")
    compare_at_price: int | None = Field(default=None, gt=0)
    description: str
    image: str
    stock: int = Field(ge=0)
    variants: tuple[str, ...] = ()
    variant_label: str = "Opción"
    badge: str | None = None
    featured: bool = False

    @property
    def on_sale(self) -> bool:
        return self.compare_at_price is not None and self.compare_at_price > self.price


class CartItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(pattern=PRODUCT_ID_PATTERN)
    quantity: int = Field(ge=1, le=20)
    variant: str | None = Field(default=None, max_length=40)


class CartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CartItemIn] = Field(min_length=1, max_length=50)


class CartLine(BaseModel):
    product_id: str
    name: str
    image: str
    variant: str | None
    quantity: int
    unit_price: int
    line_total: int


class CartQuote(BaseModel):
    lines: list[CartLine]
    item_count: int
    subtotal: int
    currency: str
    whatsapp_url: str
