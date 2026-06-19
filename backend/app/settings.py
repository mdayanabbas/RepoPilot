from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RepoPilot"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./repopilot.db"
    AUTO_CREATE_TABLES: bool = True

    WORKSPACE_ROOT: str = "./storage/workspaces"
    TRACE_ROOT: str = "./storage/traces"
    LOG_ROOT: str = "./storage/logs"

    PRIMARY_LLM_PROVIDER: str = "groq"
    FALLBACK_LLM_PROVIDER: str = "lmstudio"

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LMSTUDIO_MODEL: str = "local-model"

    MAX_RETRIEVED_FILES: int = 6
    MAX_FILE_CHARS: int = 12000
    MAX_CONTEXT_CHARS: int = 50000

    SUPPORTED_FRAMEWORKS: list[str] = ["fastapi", "flask"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
