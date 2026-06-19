from typing import Any


class RepoPilotError(Exception):
    status_code = 500

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}


class RepositoryError(RepoPilotError):
    status_code = 400


class ScanError(RepoPilotError):
    status_code = 400


class FrameworkDetectionError(ScanError):
    status_code = 422


class IntelligenceError(RepoPilotError):
    status_code = 500


class RetrievalError(RepoPilotError):
    status_code = 500


class LLMProviderError(RepoPilotError):
    status_code = 502


class SchemaValidationError(RepoPilotError):
    status_code = 422
