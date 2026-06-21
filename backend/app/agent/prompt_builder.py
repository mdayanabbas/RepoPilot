import json
from typing import Any

from backend.app.agent.prompts import (
    get_fix_plan_schema,
    get_framework_prompt_template,
    get_system_prompt,
)
from backend.app.schemas.retrieval import StructuredContext


def build_fix_plan_prompt(context: StructuredContext) -> str:
    framework = context.framework.value
    context_payload = _build_context_payload(context)
    context_json = json.dumps(
        context_payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    schema_json = _normalize_schema(get_fix_plan_schema())

    return "\n\n".join(
        [
            get_system_prompt(),
            get_framework_prompt_template(framework),
            "## Structured Context\n" + context_json,
            "## Required Fix Plan JSON Schema\n" + schema_json,
        ]
    )


def _build_context_payload(context: StructuredContext) -> dict[str, Any]:
    return {
        "issue": context.issue,
        "framework": context.framework.value,
        "selected_files": [
            selected_file.model_dump(mode="json")
            for selected_file in context.selected_files
        ],
        "relevant_routes": [
            route.model_dump(mode="json") for route in context.relevant_routes
        ],
        "relevant_symbols": [
            symbols.model_dump(mode="json") for symbols in context.relevant_symbols
        ],
        "file_contexts": [
            file_context.model_dump(mode="json")
            for file_context in context.file_contexts
        ],
        "total_context_chars": context.total_context_chars,
    }


def _normalize_schema(schema_text: str) -> str:
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Fix plan schema is not valid JSON") from exc
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False)
