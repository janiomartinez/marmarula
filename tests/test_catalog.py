import pytest

from app.cart import format_money
from app.models import Category, Product
from app.repository import CatalogRepository, get_repository


def test_catalog_file_is_valid() -> None:
    repo = get_repository()
    assert len(repo.categories()) == 3
    for cat in repo.categories():
        assert repo.products(cat.slug), f"La categoría {cat.slug} no tiene productos"


def test_sale_prices_are_consistent() -> None:
    for p in get_repository().on_sale():
        assert p.compare_at_price > p.price


def _product(pid: str) -> Product:
    return Product(
        id=pid, name="Algo", category="velas", price=1, description="", image="", stock=1
    )


def test_duplicate_ids_rejected() -> None:
    cat = Category(slug="velas", name="Velas", tagline="", image="")
    with pytest.raises(ValueError, match="duplicado"):
        CatalogRepository([cat], [_product("abc"), _product("abc")])


def test_undefined_category_rejected() -> None:
    with pytest.raises(ValueError, match="Categorías"):
        CatalogRepository([], [_product("abc")])


def test_search_requires_all_terms() -> None:
    repo = get_repository()
    assert repo.search("vela lavanda")[0].id == "vela-lavanda-calma"
    assert repo.search("   ") == []


@pytest.mark.parametrize(
    ("value", "expected"), [(0, "$ 0"), (45000, "$ 45.000"), (1234567, "$ 1.234.567")]
)
def test_format_money(value: int, expected: str) -> None:
    assert format_money(value) == expected
