from typing import Any

from pydantic import ValidationError

from backend.app.core.errors import SchemaValidationError
from backend.app.schemas.fix_plan import FixPlan


def validate_fix_plan_payload(payload: dict[str, Any]) -> FixPlan:
    try:
        return FixPlan.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(
            "Invalid fix plan payload",
            details={"errors": exc.errors(include_url=False)},
        ) from exc
