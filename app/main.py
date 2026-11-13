"""Punto de entrada de Marmarula. Ejecuta con: `uvicorn app.main:app --reload`."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, get_settings
from app.routers import api, pages
from app.security import SecurityHeadersMiddleware

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs = not settings.is_production

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )

    # El orden importa: el último añadido es el primero en ejecutarse.
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api.router)
    app.include_router(pages.router)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        if request.url.path.startswith("/api/") or exc.status_code != 404:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return pages.templates.TemplateResponse(request, "404.html", {}, status_code=404)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Response:
        if request.url.path.startswith("/api/"):
            # No devolvemos el cuerpo recibido para no reflejar datos del usuario.
            errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
            return JSONResponse({"detail": errors}, status_code=422)
        return pages.templates.TemplateResponse(request, "404.html", {}, status_code=404)

    return app


app = create_app()
