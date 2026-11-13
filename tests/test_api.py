from urllib.parse import unquote

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_list_categories(client: TestClient) -> None:
    slugs = {c["slug"] for c in client.get("/api/v1/categories").json()}
    assert slugs == {"accesorios", "velas", "ropa"}


def test_list_products_filtered_by_category(client: TestClient) -> None:
    res = client.get("/api/v1/products", params={"category": "velas"})
    assert res.status_code == 200
    assert res.json()
    assert all(p["category"] == "velas" for p in res.json())


def test_invalid_category_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/products", params={"category": "zapatos"}).status_code == 422


def test_get_product(client: TestClient) -> None:
    res = client.get("/api/v1/products/vela-vainilla-coco")
    assert res.status_code == 200
    assert res.json()["name"] == "Vela Vainilla & Coco"


def test_unknown_product_returns_404_json(client: TestClient) -> None:
    res = client.get("/api/v1/products/no-existe")
    assert res.status_code == 404
    assert res.json() == {"detail": "Producto no encontrado"}


def test_product_id_pattern_blocks_weird_input(client: TestClient) -> None:
    assert client.get("/api/v1/products/..%2F..%2Fetc").status_code in (404, 422)
    assert client.get("/api/v1/products/<script>").status_code == 422


def test_search(client: TestClient) -> None:
    names = [p["name"] for p in client.get("/api/v1/products/search", params={"q": "vela"}).json()]
    assert "Vela Lavanda Calma" in names


def test_search_query_length_limited(client: TestClient) -> None:
    assert client.get("/api/v1/products/search", params={"q": "x" * 61}).status_code == 422


# ---------- Carrito ----------


def quote(client: TestClient, items: list[dict]):
    return client.post("/api/v1/cart/quote", json={"items": items})


def test_quote_uses_server_prices(client: TestClient) -> None:
    res = quote(
        client,
        [
            {"product_id": "aretes-luna-dorada", "quantity": 2},
            {"product_id": "vela-vainilla-coco", "quantity": 1, "variant": "Ámbar"},
        ],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["subtotal"] == 2 * 38000 + 45000
    assert data["item_count"] == 3
    assert data["currency"] == "COP"
    assert data["whatsapp_url"].startswith("https://wa.me/573001112233?text=")
    assert "Aretes Luna Dorada" in unquote(data["whatsapp_url"])


def test_quote_ignores_client_supplied_price(client: TestClient) -> None:
    res = quote(client, [{"product_id": "aretes-luna-dorada", "quantity": 1, "price": 1}])
    assert res.status_code == 422  # campos extra prohibidos


def test_quote_merges_duplicate_lines(client: TestClient) -> None:
    item = {"product_id": "aretes-luna-dorada", "quantity": 1}
    data = quote(client, [item, item]).json()
    assert len(data["lines"]) == 1
    assert data["lines"][0]["quantity"] == 2


def test_quote_unknown_product(client: TestClient) -> None:
    res = quote(client, [{"product_id": "no-existe", "quantity": 1}])
    assert res.status_code == 422
    assert "no existe" in res.json()["detail"]


def test_quote_requires_valid_variant(client: TestClient) -> None:
    assert quote(client, [{"product_id": "abrigo-pano-negro", "quantity": 1}]).status_code == 422
    res = quote(client, [{"product_id": "abrigo-pano-negro", "quantity": 1, "variant": "XXL"}])
    assert res.status_code == 422


def test_quote_rejects_variant_on_simple_product(client: TestClient) -> None:
    res = quote(client, [{"product_id": "aretes-luna-dorada", "quantity": 1, "variant": "M"}])
    assert res.status_code == 422


def test_quote_respects_stock(client: TestClient) -> None:
    res = quote(client, [{"product_id": "anillos-plata-duo", "quantity": 1}])
    assert res.status_code == 409


def test_quote_quantity_bounds(client: TestClient) -> None:
    for qty in (0, -1, 21):
        res = quote(client, [{"product_id": "aretes-luna-dorada", "quantity": qty}])
        assert res.status_code == 422


def test_quote_empty_cart_rejected(client: TestClient) -> None:
    assert quote(client, []).status_code == 422


def test_validation_errors_do_not_echo_input(client: TestClient) -> None:
    payload = "<script>alert(1)</script>"
    res = quote(client, [{"product_id": payload, "quantity": 1}])
    assert res.status_code == 422
    assert payload not in res.text
