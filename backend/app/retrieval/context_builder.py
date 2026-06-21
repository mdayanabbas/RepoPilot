from pathlib import Path, PurePosixPath

from backend.app.core.errors import RetrievalError
from backend.app.core.path_utils import is_path_within
from backend.app.dependencies import get_settings
from backend.app.retrieval.token_budget import CharacterBudget
from backend.app.scanner.ignore_rules import is_ignored_directory, is_ignored_file
from backend.app.schemas.retrieval import (
    ContextBuildInput,
    FileContext,
    RelevantFile,
    StructuredContext,
)
from backend.app.settings import Settings

BINARY_SAMPLE_BYTES = 8192


class ContextBuilder:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def build(self, context_input: ContextBuildInput) -> StructuredContext:
        workspace = Path(context_input.workspace_path).resolve()
        max_file_chars = context_input.max_file_chars or self.settings.MAX_FILE_CHARS
        max_context_chars = (
            context_input.max_context_chars or self.settings.MAX_CONTEXT_CHARS
        )
        budget = CharacterBudget(max_file_chars, max_context_chars)
        selected_files = _normalize_selected_files(context_input, workspace)
        selected_paths = list(
            dict.fromkeys(file.file_path for file in selected_files)
        )
        resolved_paths = {
            relative_path: workspace.joinpath(*PurePosixPath(relative_path).parts)
            for relative_path in selected_paths
        }
        file_contexts = [
            self._build_file_context(
                relative_path, resolved_paths[relative_path], budget
            )
            for relative_path in selected_paths
        ]
        selected_set = set(selected_paths)

        return StructuredContext(
            issue=context_input.issue_text,
            framework=context_input.framework,
            selected_files=selected_files,
            relevant_routes=[
                route
                for route in context_input.route_index.routes
                if route.file_path in selected_set
            ],
            relevant_symbols=[
                symbols
                for symbols in context_input.symbol_index.files
                if symbols.path in selected_set
            ],
            file_contexts=file_contexts,
            total_context_chars=budget.used_chars,
        )

    def _build_file_context(
        self,
        relative_path: str,
        file_path: Path,
        budget: CharacterBudget,
    ) -> FileContext:
        path_parts = PurePosixPath(relative_path).parts
        if is_ignored_file(relative_path) or any(
            is_ignored_directory(part) for part in path_parts[:-1]
        ):
            return FileContext(file_path=relative_path, error="Ignored file")
        if not file_path.is_file():
            return FileContext(file_path=relative_path, error="File does not exist")

        try:
            content, source_has_more = _read_text(file_path, budget.next_file_limit)
        except (OSError, UnicodeError):
            return FileContext(
                file_path=relative_path, error="Binary or unreadable file"
            )

        included, truncated = budget.add(content, source_has_more)
        return FileContext(
            file_path=relative_path,
            content=included,
            truncated=truncated,
        )


def build_context(
    context_input: ContextBuildInput,
    settings: Settings | None = None,
) -> StructuredContext:
    return ContextBuilder(settings).build(context_input)


def _normalize_selected_files(
    context_input: ContextBuildInput,
    workspace: Path,
) -> list[RelevantFile]:
    normalized: list[RelevantFile] = []
    for selected_file in context_input.selected_files:
        safe_path = _resolve_selected_path(workspace, selected_file.file_path)
        normalized.append(
            selected_file.model_copy(update={"file_path": safe_path})
        )
    return normalized


def _resolve_selected_path(workspace: Path, relative_path: str) -> str:
    # Retrieval/scanner paths are POSIX-style, but callers on Windows may supply
    # backslashes. Normalize both forms before applying ignore and traversal rules.
    requested = Path(relative_path.replace("\\", "/"))
    candidate = (workspace / requested).resolve()
    if requested.is_absolute() or not is_path_within(workspace, candidate):
        raise RetrievalError(
            "Selected file is outside the workspace",
            details={"path": relative_path},
        )
    return candidate.relative_to(workspace).as_posix()


def _read_text(path: Path, char_limit: int) -> tuple[str, bool]:
    with path.open("rb") as binary_file:
        sample = binary_file.read(BINARY_SAMPLE_BYTES)
    if b"\x00" in sample:
        raise UnicodeError("Binary file")

    with path.open("r", encoding="utf-8") as text_file:
        content = text_file.read(char_limit + 1)
    return content[:char_limit], len(content) > char_limit
