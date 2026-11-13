import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

TEST_SETTINGS = Settings(environment="test", whatsapp_number="573001112233")


@pytest.fixture
def client() -> TestClient:
    app = create_app(TEST_SETTINGS)
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with TestClient(app) as c:
        yield c
