from pydantic import BaseModel, Field

from backend.app.schemas.git_intelligence import GitHistoryResult
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import (
    PythonFileSymbols,
    RouteIndex,
    RouteInfo,
    SymbolIndex,
)
from backend.app.schemas.scan import ScannedFile


class RetrievalInput(BaseModel):
    issue_text: str
    scanned_files: list[ScannedFile]
    framework: SupportedFramework
    symbol_index: SymbolIndex = Field(default_factory=SymbolIndex)
    route_index: RouteIndex = Field(default_factory=RouteIndex)
    git_history: GitHistoryResult | None = None
    top_n: int = Field(default=6, ge=1)


class RelevantFile(BaseModel):
    file_path: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    matched_signals: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    files: list[RelevantFile] = Field(default_factory=list)


class ContextBuildInput(BaseModel):
    issue_text: str
    workspace_path: str
    framework: SupportedFramework
    selected_files: list[RelevantFile]
    route_index: RouteIndex = Field(default_factory=RouteIndex)
    symbol_index: SymbolIndex = Field(default_factory=SymbolIndex)
    max_file_chars: int | None = Field(default=None, ge=1)
    max_context_chars: int | None = Field(default=None, ge=1)


class FileContext(BaseModel):
    file_path: str
    content: str = ""
    truncated: bool = False
    error: str | None = None


class StructuredContext(BaseModel):
    issue: str
    framework: SupportedFramework
    selected_files: list[RelevantFile]
    relevant_routes: list[RouteInfo] = Field(default_factory=list)
    relevant_symbols: list[PythonFileSymbols] = Field(default_factory=list)
    file_contexts: list[FileContext] = Field(default_factory=list)
    total_context_chars: int = Field(ge=0)
