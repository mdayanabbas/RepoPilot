from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_ROOT / "system" / "repopilot_system_prompt.md"
FIX_PLAN_SCHEMA_PATH = PROMPTS_ROOT / "schemas" / "fix_plan_schema.json"
FRAMEWORK_PROMPT_PATHS = {
    "fastapi": PROMPTS_ROOT / "fix_plan" / "fastapi_fix_plan_prompt.md",
    "flask": PROMPTS_ROOT / "fix_plan" / "flask_fix_plan_prompt.md",
}


def get_system_prompt() -> str:
    return _read_prompt(SYSTEM_PROMPT_PATH)


def get_framework_prompt_template(framework: str) -> str:
    normalized_framework = framework.strip().lower()
    template_path = FRAMEWORK_PROMPT_PATHS.get(normalized_framework)
    if template_path is None:
        supported = ", ".join(sorted(FRAMEWORK_PROMPT_PATHS))
        raise ValueError(
            f"Unsupported framework '{framework}'. Supported frameworks: {supported}"
        )
    return _read_prompt(template_path)


def get_fix_plan_schema() -> str:
    return _read_prompt(FIX_PLAN_SCHEMA_PATH)


def _read_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to load prompt resource: {path}") from exc
