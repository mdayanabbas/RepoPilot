from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from backend.app.agent.schema_validator import validate_fix_plan_payload
from backend.app.core.errors import SchemaValidationError
from backend.app.schemas.fix_plan import FixPlan


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    return {
        "suspected_issue": "The login route imports a missing service.",
        "root_cause": "The route references an outdated module path.",
        "files_to_change": [
            {
                "file_path": "routes/auth.py",
                "reason": "Correct the service import.",
                "risk": "low",
            }
        ],
        "fix_plan": [
            {
                "step": 1,
                "description": "Update the import path.",
                "target_file": "routes/auth.py",
            }
        ],
        "validation_plan": [
            {
                "command": "pytest tests/test_auth.py",
                "purpose": "Verify the login route.",
            }
        ],
        "confidence": 0.9,
        "risk_level": "low",
        "requires_human_review": False,
        "assumptions": ["The replacement service API is compatible."],
    }


def test_valid_payload_returns_fix_plan(
    valid_payload: dict[str, Any],
) -> None:
    result = validate_fix_plan_payload(valid_payload)

    assert isinstance(result, FixPlan)
    assert result.files_to_change[0].file_path == "routes/auth.py"
    assert result.fix_plan[0].step == 1
    assert result.confidence == 0.9


def test_missing_required_field_is_rejected(
    valid_payload: dict[str, Any],
) -> None:
    payload = deepcopy(valid_payload)
    del payload["root_cause"]

    with pytest.raises(SchemaValidationError) as exc_info:
        validate_fix_plan_payload(payload)

    assert exc_info.value.details["errors"][0]["type"] == "missing"


@pytest.mark.parametrize("field", ["risk_level", "files_to_change"])
def test_invalid_risk_level_is_rejected(
    valid_payload: dict[str, Any],
    field: str,
) -> None:
    payload = deepcopy(valid_payload)
    if field == "risk_level":
        payload[field] = "critical"
    else:
        payload[field][0]["risk"] = "critical"

    with pytest.raises(SchemaValidationError):
        validate_fix_plan_payload(payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_out_of_range_confidence_is_rejected(
    valid_payload: dict[str, Any],
    confidence: float,
) -> None:
    payload = deepcopy(valid_payload)
    payload["confidence"] = confidence

    with pytest.raises(SchemaValidationError):
        validate_fix_plan_payload(payload)


@pytest.mark.parametrize(
    ("field", "malformed_item"),
    [
        ("files_to_change", {"file_path": "main.py"}),
        ("fix_plan", {"step": "first", "description": "Change it"}),
        ("validation_plan", {"command": "pytest"}),
    ],
)
def test_malformed_nested_item_is_rejected(
    valid_payload: dict[str, Any],
    field: str,
    malformed_item: dict[str, Any],
) -> None:
    payload = deepcopy(valid_payload)
    payload[field] = [malformed_item]

    with pytest.raises(SchemaValidationError):
        validate_fix_plan_payload(payload)


def test_extra_fields_are_rejected(valid_payload: dict[str, Any]) -> None:
    payload = deepcopy(valid_payload)
    payload["unexpected"] = True

    with pytest.raises(SchemaValidationError):
        validate_fix_plan_payload(payload)


def test_exported_json_schema_matches_fix_plan_model() -> None:
    schema_path = (
        Path(__file__).parents[3] / "prompts" / "schemas" / "fix_plan_schema.json"
    )
    exported_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert exported_schema.pop("$schema") == (
        "https://json-schema.org/draft/2020-12/schema"
    )

    assert exported_schema == FixPlan.model_json_schema()
