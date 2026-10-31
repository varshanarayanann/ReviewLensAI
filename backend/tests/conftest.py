import pytest
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENVIRONMENT", "DATABASE_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings() -> Settings:
    return load_settings(
        _env_file=None,
        environment="test",
        database_url="postgresql://user:pass@localhost:5432/reviewlens_test",
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
