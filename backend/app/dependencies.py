from functools import lru_cache

from backend.app.database.session import get_db
from backend.app.settings import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["get_db", "get_settings"]
