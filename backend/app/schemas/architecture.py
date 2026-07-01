from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.repository import RepositorySourceType


class ArchitectureNodeType(StrEnum):
    file = "file"
    route = "route"
    function = "function"
    class_ = "class"
    module = "module"
    config = "config"
    database = "database"
    service = "service"
    repository = "repository"
    model = "model"
    unknown = "unknown"


class ArchitectureEdgeType(StrEnum):
    imports = "imports"
    defines = "defines"
    handles_route = "handles_route"
    likely_depends_on = "likely_depends_on"
    configures = "configures"
    uses_database = "uses_database"


class ArchitectureNode(BaseModel):
    id: str
    type: ArchitectureNodeType
    label: str
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchitectureEdge(BaseModel):
    id: str
    source: str
    target: str
    type: ArchitectureEdgeType
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchitectureSummary(BaseModel):
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    detected_layers: list[str] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    route_count: int = Field(ge=0)


class ArchitectureGraph(BaseModel):
    nodes: list[ArchitectureNode] = Field(default_factory=list)
    edges: list[ArchitectureEdge] = Field(default_factory=list)
    summary: ArchitectureSummary


class ArchitectureFormat(StrEnum):
    json = "json"
    mermaid = "mermaid"


class BuildArchitectureRequest(BaseModel):
    source_type: RepositorySourceType
    source: str = Field(min_length=1)
    branch: str | None = None
    format: ArchitectureFormat = ArchitectureFormat.json


class ArchitectureBuildResponse(BaseModel):
    framework: SupportedFramework
    graph: ArchitectureGraph | None = None
    mermaid: str | None = None
    summary: ArchitectureSummary


class PersistedArchitectureResponse(BaseModel):
    analysis_run_id: str
    framework: str
    graph: ArchitectureGraph | None = None
    mermaid: str | None = None
    summary: ArchitectureSummary
