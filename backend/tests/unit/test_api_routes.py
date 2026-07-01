from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_v1_health_returns_200() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_llm_providers_returns_configured_provider_names() -> None:
    response = client.get("/api/v1/llm/providers")

    assert response.status_code == 200
    assert response.json() == {
        "primary_provider": "groq",
        "fallback_provider": "lmstudio",
        "supported_providers": ["groq", "lmstudio"],
    }


def test_repository_load_with_invalid_path_returns_error(tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/repositories/load",
        json={
            "source_type": "local",
            "source": str(tmp_path / "missing"),
            "branch": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "RepositoryError"


def test_analysis_run_with_invalid_path_returns_error(tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/analysis/run",
        json={
            "source_type": "local",
            "source": str(tmp_path / "missing"),
            "branch": None,
            "issue": "POST /login returns 500",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "RepositoryError"
