import pytest

from backend.app.settings import Settings


def test_settings_default_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    assert settings.APP_NAME == "RepoPilot"
    assert settings.APP_ENV == "development"
    assert settings.APP_DEBUG is True
    assert settings.API_PREFIX == "/api/v1"
    assert settings.DATABASE_URL == "sqlite:///./repopilot.db"
    assert settings.AUTO_CREATE_TABLES is True
    assert settings.PRIMARY_LLM_PROVIDER == "groq"
    assert settings.FALLBACK_LLM_PROVIDER == "lmstudio"
    assert settings.GROQ_API_KEY is None
    assert settings.LMSTUDIO_BASE_URL == "http://localhost:1234/v1"
    assert settings.MAX_RETRIEVED_FILES == 6
    assert settings.MAX_FILE_CHARS == 12000
    assert settings.MAX_CONTEXT_CHARS == 50000


def test_supported_frameworks_contains_fastapi_and_flask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    assert "fastapi" in settings.SUPPORTED_FRAMEWORKS
    assert "flask" in settings.SUPPORTED_FRAMEWORKS
