"""API REST JSON (versionada en /api/v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.cart import CartError, build_quote
from app.config import Settings, get_settings
from app.models import PRODUCT_ID_PATTERN, CartIn, CartQuote, Category, CategorySlug, Product
from app.repository import CatalogRepository, get_repository

router = APIRouter(prefix="/api/v1", tags=["api"])

Repo = Annotated[CatalogRepository, Depends(get_repository)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/categories", response_model=list[Category])
def list_categories(repo: Repo) -> list[Category]:
    return repo.categories()


@router.get("/products", response_model=list[Product])
def list_products(repo: Repo, category: CategorySlug | None = None) -> list[Product]:
    return repo.products(category)


@router.get("/products/search", response_model=list[Product])
def search_products(
    repo: Repo, q: Annotated[str, Query(min_length=1, max_length=60)]
) -> list[Product]:
    return repo.search(q)


@router.get("/products/{product_id}", response_model=Product)
def get_product(
    repo: Repo, product_id: Annotated[str, Path(pattern=PRODUCT_ID_PATTERN)]
) -> Product:
    product = repo.product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.post("/cart/quote", response_model=CartQuote)
def quote_cart(cart: CartIn, repo: Repo, settings: Config) -> CartQuote:
    """Recalcula el carrito con los precios reales del catálogo y arma el enlace de WhatsApp."""
    try:
        return build_quote(
            cart,
            repo,
            currency=settings.currency,
            whatsapp_number=settings.whatsapp_number,
            store_name=settings.app_name,
            free_shipping_threshold=settings.free_shipping_threshold,
        )
    except CartError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
