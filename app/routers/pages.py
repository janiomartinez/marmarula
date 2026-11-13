"""Páginas HTML renderizadas en el servidor (Jinja2, con autoescape activado)."""

from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.cart import format_money
from app.config import get_settings
from app.models import Product
from app.repository import CatalogRepository, get_repository

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _globals(request: Request) -> dict:
    settings = get_settings()
    return {
        "settings": settings,
        "categories": get_repository().categories(),
        "current_path": request.url.path,
    }


templates = Jinja2Templates(directory=TEMPLATES_DIR, context_processors=[_globals])


def image_url(url: str, width: int = 600) -> str:
    """Pide a Unsplash la imagen ya recortada y comprimida al ancho necesario."""
    if url.startswith("https://images.unsplash.com/"):
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}w={width}&q=75&auto=format&fit=crop"
    return url


templates.env.filters["money"] = format_money
templates.env.filters["img"] = image_url

router = APIRouter(include_in_schema=False)
Repo = Annotated[CatalogRepository, Depends(get_repository)]
SortOption = Literal["destacados", "precio-asc", "precio-desc"]


def _sort(products: list[Product], sort: SortOption) -> list[Product]:
    if sort == "precio-asc":
        return sorted(products, key=lambda p: p.price)
    if sort == "precio-desc":
        return sorted(products, key=lambda p: p.price, reverse=True)
    return sorted(products, key=lambda p: not p.featured)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, repo: Repo) -> HTMLResponse:
    sections = [(c, repo.products(c.slug)[:4]) for c in repo.categories()]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"featured": repo.featured(), "sections": sections, "sale": repo.on_sale()},
    )


@router.get("/c/{slug}", response_class=HTMLResponse)
def category(request: Request, slug: str, repo: Repo, sort: SortOption = "destacados"):
    cat = repo.category(slug)
    if cat is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "category.html",
        {"category": cat, "products": _sort(repo.products(slug), sort), "sort": sort},
    )


@router.get("/ofertas", response_class=HTMLResponse)
def sale(request: Request, repo: Repo) -> HTMLResponse:
    return templates.TemplateResponse(request, "sale.html", {"products": repo.on_sale()})


@router.get("/p/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: str, repo: Repo) -> HTMLResponse:
    product = repo.product(product_id)
    if product is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "product.html",
        {
            "product": product,
            "category": repo.category(product.category),
            "related": repo.related(product),
        },
    )


@router.get("/buscar", response_class=HTMLResponse)
def search(
    request: Request, repo: Repo, q: Annotated[str, Query(max_length=60)] = ""
) -> HTMLResponse:
    q = q.strip()
    return templates.TemplateResponse(
        request, "search.html", {"q": q, "results": repo.search(q) if q else []}
    )


@router.get("/carrito", response_class=HTMLResponse)
def cart(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "cart.html", {})
