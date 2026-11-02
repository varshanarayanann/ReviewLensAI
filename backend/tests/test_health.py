from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_db


class FakeSession:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def execute(self, statement: object) -> None:
        if self.error:
            raise self.error


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_reports_ok_when_query_succeeds(client: TestClient) -> None:
    client.app.dependency_overrides[get_db] = lambda: FakeSession()

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_database_health_hides_driver_errors(client: TestClient) -> None:
    error = OperationalError("SELECT 1", {}, Exception("password=secret refused"))
    client.app.dependency_overrides[get_db] = lambda: FakeSession(error)

    response = client.get("/api/health/db")

    assert response.status_code == 503
    assert response.json() == {"database": "unavailable"}
    assert "secret" not in response.text


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
