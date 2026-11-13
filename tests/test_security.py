from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_security_headers_present(client: TestClient) -> None:
    headers = client.get("/").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
    assert "frame-ancestors 'none'" in csp


def test_no_hsts_outside_production(client: TestClient) -> None:
    assert "strict-transport-security" not in client.get("/").headers


def test_untrusted_host_rejected(client: TestClient) -> None:
    assert client.get("/", headers={"host": "evil.example.com"}).status_code == 400


def test_production_disables_docs_and_enables_hsts() -> None:
    settings = Settings(environment="production", allowed_hosts=["testserver"])
    with TestClient(create_app(settings)) as prod:
        assert prod.get("/docs").status_code == 404
        assert prod.get("/openapi.json").status_code == 404
        assert "strict-transport-security" in prod.get("/").headers


def test_docs_available_in_development(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


def test_static_path_traversal_blocked(client: TestClient) -> None:
    assert client.get("/static/../main.py").status_code == 404
    assert client.get("/static/%2e%2e/main.py").status_code == 404
