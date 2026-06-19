from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "RepoPilot",
        "version": "0.1.0",
        "environment": "development",
    }


def test_api_v1_health_returns_200() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
