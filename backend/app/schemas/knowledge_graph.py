from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeNodeType(StrEnum):
    file = "file"
    route = "route"
    handler_function = "handler_function"
    function = "function"
    class_ = "class"
    request_model = "request_model"
    response_model = "response_model"
    imported_module = "imported_module"
    config = "config"
    database = "database"
    repository = "repository"
    service = "service"
    schema = "schema"
    unknown = "unknown"


class KnowledgeEdgeType(StrEnum):
    file_defines_function = "file_defines_function"
    file_defines_class = "file_defines_class"
    file_imports_module = "file_imports_module"
    route_handled_by = "route_handled_by"
    handler_uses_model = "handler_uses_model"
    handler_likely_calls = "handler_likely_calls"
    file_likely_depends_on = "file_likely_depends_on"
    service_uses_repository = "service_uses_repository"
    repository_uses_database = "repository_uses_database"
    config_used_by = "config_used_by"
    related_to_issue = "related_to_issue"


class KnowledgeGraphNode(BaseModel):
    id: str
    type: KnowledgeNodeType
    label: str
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: KnowledgeEdgeType
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphSummary(BaseModel):
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    route_count: int = Field(ge=0)
    handler_count: int = Field(ge=0)
    model_count: int = Field(ge=0)
    service_count: int = Field(ge=0)
    database_node_count: int = Field(ge=0)


class KnowledgeGraph(BaseModel):
    nodes: list[KnowledgeGraphNode] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list)
    summary: KnowledgeGraphSummary


class KnowledgeGraphNeighborhood(BaseModel):
    nodes: list[KnowledgeGraphNode] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list)
