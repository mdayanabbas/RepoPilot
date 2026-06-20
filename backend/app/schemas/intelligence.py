from pydantic import BaseModel, Field

from backend.app.schemas.framework import SupportedFramework


class ImportInfo(BaseModel):
    module: str
    name: str | None = None


class FunctionInfo(BaseModel):
    name: str
    line_number: int = Field(ge=1)
    args: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    is_async: bool = False


class ClassInfo(BaseModel):
    name: str
    line_number: int = Field(ge=1)
    base_classes: list[str] = Field(default_factory=list)
    methods: list[FunctionInfo] = Field(default_factory=list)


class PythonFileSymbols(BaseModel):
    path: str
    imports: list[ImportInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)


class IntelligenceErrorEntry(BaseModel):
    path: str
    message: str
    line_number: int | None = Field(default=None, ge=1)


class SymbolIndex(BaseModel):
    files: list[PythonFileSymbols] = Field(default_factory=list)
    errors: list[IntelligenceErrorEntry] = Field(default_factory=list)


class RouteInfo(BaseModel):
    framework: SupportedFramework
    path: str
    method: str
    handler_name: str
    file_path: str
    line_number: int = Field(ge=1)
    router_name: str | None = None


class RouteIndex(BaseModel):
    routes: list[RouteInfo] = Field(default_factory=list)
    errors: list[IntelligenceErrorEntry] = Field(default_factory=list)
