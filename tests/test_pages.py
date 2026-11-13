import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/c/velas",
        "/c/ropa",
        "/c/accesorios",
        "/ofertas",
        "/buscar",
        "/carrito",
        "/p/vela-vainilla-coco",
    ],
)
def test_pages_render(client: TestClient, path: str) -> None:
    res = client.get(path)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "marmarula" in res.text


def test_home_shows_categories_and_products(client: TestClient) -> None:
    html = client.get("/").text
    for name in ("Accesorios", "Velas", "Ropa", "Lo más querido", "Set Velas Ritual"):
        assert name in html


def test_category_sort_by_price(client: TestClient) -> None:
    html = client.get("/c/ropa", params={"sort": "precio-asc"}).text
    assert html.index("Camiseta Básica Algodón") < html.index("Chaqueta Bomber Terracota")


def test_invalid_sort_is_not_found(client: TestClient) -> None:
    assert client.get("/c/ropa", params={"sort": "hack"}).status_code == 404


def test_unknown_category_and_product_return_404_page(client: TestClient) -> None:
    for path in ("/c/zapatos", "/p/no-existe"):
        res = client.get(path)
        assert res.status_code == 404
        assert "Esta página no existe" in res.text


def test_sold_out_product_cannot_be_added(client: TestClient) -> None:
    html = client.get("/p/anillos-plata-duo").text
    assert "data-add-to-cart" not in html
    assert "Agotado" in html


def test_search_page_escapes_query(client: TestClient) -> None:
    html = client.get("/buscar", params={"q": "<script>alert(1)</script>"}).text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_search_page_finds_products(client: TestClient) -> None:
    assert "Bolso Tote Arena" in client.get("/buscar", params={"q": "bolso"}).text


def test_product_page_has_gallery_and_buy_now(client: TestClient) -> None:
    html = client.get("/p/collar-perla-mar").text
    assert "data-gallery" in html
    assert html.count("data-gallery-go") == 3
    assert "data-buy-now" in html
    assert "Envío GRATIS desde $ 150.000" in html


def test_layout_has_desktop_nav_and_whatsapp_button(client: TestClient) -> None:
    html = client.get("/c/velas").text
    assert 'class="desknav"' in html
    assert 'href="/c/velas" class="is-active"' in html
    assert 'class="wa-float" href="https://wa.me/' in html
    assert "Envío GRATIS por compras desde" in html


def test_image_filter_handles_existing_query() -> None:
    from app.routers.pages import image_url

    base = "https://images.unsplash.com/photo-1"
    assert image_url(base, 100) == f"{base}?w=100&q=75&auto=format&fit=crop"
    assert image_url(f"{base}?fp-z=2", 100).startswith(f"{base}?fp-z=2&w=100")
    assert image_url("/static/img/x.png") == "/static/img/x.png"
