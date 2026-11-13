# marmarula 🕯️

Tienda online **mobile-first** de accesorios, velas y ropa, hecha con **FastAPI**.
Los pedidos se confirman por **WhatsApp**: el cliente arma su carrito y la tienda
genera el mensaje con el detalle y el total.

## Diseño

Inspirado en las tendencias de e-commerce móvil actuales:

- **Barra de navegación inferior** (como Instagram), fácil de usar con el pulgar.
- **Categorías tipo historias** de Instagram con anillos de color.
- **Bento grid** en la portada y **carruseles deslizables** de productos.
- **Barra fija de “Agregar al carrito” / “Comprar ahora”** en el detalle de producto.
- **Galería de fotos** deslizable con miniaturas.
- **Envío gratis desde un monto**, con barra de progreso en el carrito.
- **Botón flotante de WhatsApp** y barra de anuncios animada.
- Paleta tierra (crema, terracota, salvia) con tipografías *Fraunces* y *Outfit*.

### Responsive (celular, tablet y PC)

| Pantalla | Diseño |
|---|---|
| Celular (< 700 px) | barra inferior, 2 columnas, botones de compra fijos abajo |
| Tablet (700–1023 px) | 3 columnas, portada bento en dos columnas |
| PC (≥ 1024 px) | menú superior, 4 columnas, ficha de producto y carrito en dos columnas |

## Cómo verla en tu computador

Requisitos: Python 3.11 o superior.

```bash
git clone https://github.com/janiomartinez/marmarula.git
cd marmarula
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env          # en Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Abre <http://localhost:8000>. Para verla como celular en Chrome: `F12` → icono de
dispositivo móvil (Ctrl+Shift+M).

La documentación interactiva de la API está en <http://localhost:8000/docs>
(se desactiva automáticamente en producción).

## Estructura

```
app/
  main.py            # crea la app, middlewares y manejo de errores
  config.py          # configuración por variables de entorno (.env)
  models.py          # esquemas Pydantic (validación de datos)
  repository.py      # acceso al catálogo
  cart.py            # cálculo del carrito y mensaje de WhatsApp
  security.py        # cabeceras de seguridad HTTP
  routers/
    api.py           # API JSON en /api/v1
    pages.py         # páginas HTML
  data/catalog.json  # productos y categorías (edítalo para cambiar el catálogo)
  templates/         # plantillas Jinja2
  static/            # CSS, JS e imágenes
tests/               # tests automáticos (pytest)
```

## Cambiar productos

Edita `app/data/catalog.json`. Cada producto tiene `id`, `name`, `category`
(`accesorios`, `velas` o `ropa`), `price`, `stock`, `image` y opcionalmente
`compare_at_price` (precio antes de la oferta), `variants` (tallas, frascos…),
`gallery` (fotos adicionales), `badge` y `featured`. Los tests validan que el archivo sea correcto.

Las imágenes actuales son **de ejemplo** y vienen de [Unsplash](https://unsplash.com).
Reemplázalas por las fotos reales de los productos.

## Calidad y seguridad

| Herramienta | Para qué |
|---|---|
| `pytest` + `pytest-cov` | 53 tests, cobertura mínima exigida del 90 % |
| `ruff` | lint y formato del código |
| `bandit` | análisis estático de seguridad |
| `pip-audit` | vulnerabilidades conocidas en dependencias |
| GitHub Actions | ejecuta todo lo anterior en cada push / pull request |
| Dependabot | actualizaciones semanales de dependencias |

```bash
pytest
ruff check . && ruff format --check .
bandit -c pyproject.toml -r app
pip-audit -r requirements.txt
```

Medidas de seguridad aplicadas (basadas en OWASP):

- **Precios calculados en el servidor**: el navegador solo envía ids y cantidades.
- Validación estricta de entradas con Pydantic (patrones, rangos, campos extra prohibidos).
- **Content-Security-Policy** estricta sin scripts en línea, más `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` y HSTS en producción.
- `TrustedHostMiddleware` para evitar ataques de cabecera Host.
- Plantillas con *autoescape* y JS que nunca usa `innerHTML` con datos (anti-XSS).
- Los errores de validación no devuelven lo que envió el usuario.
- Secretos y configuración fuera del código (`.env`, ignorado por git).
- Dependencias con versiones fijadas.

## Configuración

| Variable | Por defecto | Descripción |
|---|---|---|
| `MARMARULA_ENVIRONMENT` | `development` | `production` desactiva `/docs` y activa HSTS |
| `MARMARULA_WHATSAPP_NUMBER` | `573000000000` | número que recibe los pedidos (solo dígitos, con código de país) |
| `MARMARULA_INSTAGRAM_USER` | `marmarula` | usuario de Instagram |
| `MARMARULA_CURRENCY` | `COP` | moneda mostrada |
| `MARMARULA_FREE_SHIPPING_THRESHOLD` | `150000` | compra mínima para envío gratis |
| `MARMARULA_ALLOWED_HOSTS` | `["localhost","127.0.0.1","testserver"]` | dominios permitidos |
