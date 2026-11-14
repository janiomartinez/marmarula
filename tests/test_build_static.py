import json
from pathlib import Path

import pytest

from app.build_static import build, page_paths


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    build(out, "/marmarula")
    return out


def test_all_pages_generated(site: Path) -> None:
    for path in page_paths():
        assert (site / path.strip("/") / "index.html").is_file(), path
    assert (site / "404.html").is_file()
    assert (site / ".nojekyll").is_file()
    assert (site / "static" / "css" / "styles.css").is_file()


def test_links_use_base_path(site: Path) -> None:
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="/marmarula/c/velas"' in html
    assert 'src="/marmarula/static/js/app.js"' in html
    assert 'href="/c/' not in html
    assert "testserver" not in html


def test_static_mode_flags_and_csp(site: Path) -> None:
    html = (site / "carrito" / "index.html").read_text(encoding="utf-8")
    assert 'data-static="true"' in html
    assert 'data-base="/marmarula"' in html
    assert 'http-equiv="Content-Security-Policy"' in html
    assert "frame-ancestors" not in html


def test_catalog_json(site: Path) -> None:
    data = json.loads((site / "api" / "catalog.json").read_text(encoding="utf-8"))
    assert data["settings"]["free_shipping_threshold"] == 150000
    assert len(data["products"]) == 15
    assert {"id", "price", "variants", "stock"} <= data["products"][0].keys()


def test_search_page_has_client_side_results(site: Path) -> None:
    html = (site / "buscar" / "index.html").read_text(encoding="utf-8")
    assert "data-search-results" in html
    assert 'id="card-tpl"' in html


def test_server_mode_has_no_static_extras(client) -> None:
    html = client.get("/buscar").text
    assert "data-static" not in html
    assert "data-search-results" not in html
