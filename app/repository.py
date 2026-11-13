"""Acceso al catálogo. Hoy lee un JSON; mañana puede cambiarse por una base de datos
sin tocar las rutas, porque todo pasa por `CatalogRepository`."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import TypeAdapter

from app.models import Category, Product

DATA_FILE = Path(__file__).parent / "data" / "catalog.json"


class CatalogRepository:
    def __init__(self, categories: list[Category], products: list[Product]) -> None:
        self._categories = {c.slug: c for c in categories}
        self._products = {p.id: p for p in products}
        if len(self._products) != len(products):
            raise ValueError("Hay productos con id duplicado en el catálogo")
        unknown = {p.category for p in products} - self._categories.keys()
        if unknown:
            raise ValueError(f"Categorías sin definir: {unknown}")

    @classmethod
    def from_file(cls, path: Path = DATA_FILE) -> "CatalogRepository":
        raw = json.loads(path.read_text(encoding="utf-8"))
        categories = TypeAdapter(list[Category]).validate_python(raw["categories"])
        products = TypeAdapter(list[Product]).validate_python(raw["products"])
        return cls(categories, products)

    def categories(self) -> list[Category]:
        return list(self._categories.values())

    def category(self, slug: str) -> Category | None:
        return self._categories.get(slug)

    def products(self, category: str | None = None) -> list[Product]:
        items = list(self._products.values())
        if category is not None:
            items = [p for p in items if p.category == category]
        return items

    def product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    def featured(self) -> list[Product]:
        return [p for p in self._products.values() if p.featured]

    def on_sale(self) -> list[Product]:
        return [p for p in self._products.values() if p.on_sale]

    def search(self, query: str) -> list[Product]:
        terms = query.lower().split()
        if not terms:
            return []

        def haystack(p: Product) -> str:
            return f"{p.name} {p.description} {p.category} {' '.join(p.variants)}".lower()

        return [p for p in self._products.values() if all(t in haystack(p) for t in terms)]

    def related(self, product: Product, limit: int = 4) -> list[Product]:
        same = [p for p in self.products(product.category) if p.id != product.id]
        return same[:limit]


@lru_cache
def get_repository() -> CatalogRepository:
    return CatalogRepository.from_file()
