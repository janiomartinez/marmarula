"""Genera la versión estática de la tienda (para GitHub Pages).

Usa la misma app FastAPI y las mismas plantillas: pide cada página como lo haría
un navegador y guarda el HTML. El carrito, la búsqueda y el orden funcionan en el
navegador con `api/catalog.json`.

Uso:
    python -m app.build_static --out dist --base /marmarula
"""

import argparse
import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import STATIC_DIR, create_app
from app.repository import get_repository

PUBLIC_PRODUCT_FIELDS = {
    "id", "name", "category", "price", "compare_at_price", "description",
    "image", "stock", "variants", "badge", "featured",
}  # fmt: skip


def page_paths() -> list[str]:
    repo = get_repository()
    return [
        "/",
        "/ofertas",
        "/buscar",
        "/carrito",
        *(f"/c/{c.slug}" for c in repo.categories()),
        *(f"/p/{p.id}" for p in repo.products()),
    ]


def build(out_dir: Path, base_path: str = "") -> list[Path]:
    settings = Settings(
        environment="production",
        static_site=True,
        base_path=base_path,
        allowed_hosts=["testserver"],
    )
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    written: list[Path] = []

    with TestClient(create_app(settings)) as client:
        for path in page_paths():
            res = client.get(path)
            res.raise_for_status()
            target = out_dir / path.strip("/") / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(res.text, encoding="utf-8")
            written.append(target)

        not_found = client.get("/pagina-que-no-existe")
        assert not_found.status_code == 404  # noqa: S101 - verificación del build
        (out_dir / "404.html").write_text(not_found.text, encoding="utf-8")
        written.append(out_dir / "404.html")

    shutil.copytree(STATIC_DIR, out_dir / "static")

    repo = get_repository()
    catalog = {
        "settings": {
            "app_name": settings.app_name,
            "currency": settings.currency,
            "whatsapp_number": settings.whatsapp_number,
            "free_shipping_threshold": settings.free_shipping_threshold,
        },
        "products": [
            p.model_dump(mode="json", include=PUBLIC_PRODUCT_FIELDS) for p in repo.products()
        ],
    }
    (out_dir / "api").mkdir()
    (out_dir / "api" / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False), encoding="utf-8"
    )
    # Evita que GitHub Pages procese el sitio con Jekyll.
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--base", default="", help="Ruta base, p. ej. /marmarula")
    args = parser.parse_args()
    pages = build(args.out, args.base)
    print(f"Sitio estático generado en {args.out} ({len(pages)} páginas)")


if __name__ == "__main__":
    main()
