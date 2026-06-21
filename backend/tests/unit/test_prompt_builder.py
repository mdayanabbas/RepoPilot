import pytest

from backend.app.agent.prompt_builder import build_fix_plan_prompt
from backend.app.agent.prompts import get_framework_prompt_template
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import (
    FunctionInfo,
    PythonFileSymbols,
    RouteInfo,
)
from backend.app.schemas.retrieval import (
    FileContext,
    RelevantFile,
    StructuredContext,
)


def _context(framework: SupportedFramework) -> StructuredContext:
    entrypoint = "main.py" if framework == SupportedFramework.fastapi else "app.py"
    content = (
        "app = FastAPI()\n"
        if framework == SupportedFramework.fastapi
        else "app = Flask(__name__)\n"
    )
    return StructuredContext(
        issue="POST /login returns a 500 response",
        framework=framework,
        selected_files=[
            RelevantFile(
                file_path=entrypoint,
                score=0.9,
                reason="Contains application and route setup",
                matched_signals=["route:/login"],
            )
        ],
        relevant_routes=[
            RouteInfo(
                framework=framework,
                path="/login",
                method="POST",
                handler_name="login",
                file_path=entrypoint,
                line_number=8,
            )
        ],
        relevant_symbols=[
            PythonFileSymbols(
                path=entrypoint,
                functions=[FunctionInfo(name="login", line_number=8)],
            )
        ],
        file_contexts=[FileContext(file_path=entrypoint, content=content)],
        total_context_chars=len(content),
    )


@pytest.mark.parametrize(
    ("framework", "entrypoint", "framework_heading"),
    [
        (SupportedFramework.fastapi, "main.py", "FastAPI repository context"),
        (SupportedFramework.flask, "app.py", "Flask repository context"),
    ],
)
def test_framework_prompt_contains_context_and_schema(
    framework: SupportedFramework,
    entrypoint: str,
    framework_heading: str,
) -> None:
    prompt = build_fix_plan_prompt(_context(framework))

    assert "POST /login returns a 500 response" in prompt
    assert framework_heading in prompt
    assert f'"framework": "{framework.value}"' in prompt
    assert f'"file_path": "{entrypoint}"' in prompt
    assert "Contains application and route setup" in prompt
    assert '"relevant_routes"' in prompt
    assert '"relevant_symbols"' in prompt
    assert '"content"' in prompt
    assert '"suspected_issue"' in prompt
    assert '"confidence"' in prompt


def test_prompt_requires_json_only_without_patches() -> None:
    prompt = build_fix_plan_prompt(_context(SupportedFramework.fastapi)).lower()

    assert "return json only" in prompt
    assert "do not use markdown" in prompt
    assert "do not include explanations outside json" in prompt
    assert "do not invent files" in prompt
    assert "only reference files listed" in prompt
    assert "do not generate patches" in prompt
    assert "fix plan only" in prompt


def test_prompt_build_is_deterministic() -> None:
    context = _context(SupportedFramework.flask)

    assert build_fix_plan_prompt(context) == build_fix_plan_prompt(context)


def test_unsupported_framework_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unsupported framework 'django'"):
        get_framework_prompt_template("django")
