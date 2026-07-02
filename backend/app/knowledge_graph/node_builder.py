from pathlib import PurePosixPath

from backend.app.schemas.intelligence import ClassInfo, RouteIndex, SymbolIndex
from backend.app.schemas.knowledge_graph import KnowledgeGraphNode, KnowledgeNodeType
from backend.app.schemas.scan import FileType, ScanResult, ScannedFile


def build_nodes(
    *,
    scan_result: ScanResult,
    symbol_index: SymbolIndex,
    route_index: RouteIndex,
) -> list[KnowledgeGraphNode]:
    nodes: dict[str, KnowledgeGraphNode] = {}
    handler_keys = {
        (route.file_path, route.handler_name) for route in route_index.routes
    }

    for scanned_file in scan_result.files:
        nodes[_file_id(scanned_file.path)] = KnowledgeGraphNode(
            id=_file_id(scanned_file.path),
            type=detect_file_node_type(scanned_file),
            label=scanned_file.path,
            file_path=scanned_file.path,
            metadata={"file_type": scanned_file.file_type.value},
        )

    for route in route_index.routes:
        nodes[_route_id(route.path, route.method)] = KnowledgeGraphNode(
            id=_route_id(route.path, route.method),
            type=KnowledgeNodeType.route,
            label=f"{route.method.upper()} {route.path}",
            file_path=route.file_path,
            metadata={
                "framework": route.framework.value,
                "handler_name": route.handler_name,
                "line_number": route.line_number,
                "router_name": route.router_name,
            },
        )

    for file_symbols in symbol_index.files:
        for imported in file_symbols.imports:
            nodes[_module_id(imported.module)] = KnowledgeGraphNode(
                id=_module_id(imported.module),
                type=KnowledgeNodeType.imported_module,
                label=imported.module,
                metadata={"imported_name": imported.name},
            )
        for function in file_symbols.functions:
            node_type = (
                KnowledgeNodeType.handler_function
                if (file_symbols.path, function.name) in handler_keys
                else KnowledgeNodeType.function
            )
            nodes[_function_id(file_symbols.path, function.name)] = KnowledgeGraphNode(
                id=_function_id(file_symbols.path, function.name),
                type=node_type,
                label=function.name,
                file_path=file_symbols.path,
                metadata={
                    "line_number": function.line_number,
                    "args": function.args,
                    "decorators": function.decorators,
                    "is_async": function.is_async,
                },
            )
        for class_info in file_symbols.classes:
            nodes[_class_id(file_symbols.path, class_info.name)] = KnowledgeGraphNode(
                id=_class_id(file_symbols.path, class_info.name),
                type=detect_class_node_type(file_symbols.path, class_info),
                label=class_info.name,
                file_path=file_symbols.path,
                metadata={
                    "line_number": class_info.line_number,
                    "base_classes": class_info.base_classes,
                    "methods": [method.name for method in class_info.methods],
                },
            )

    return sorted(nodes.values(), key=lambda node: node.id)


def detect_file_node_type(scanned_file: ScannedFile) -> KnowledgeNodeType:
    path = PurePosixPath(scanned_file.path)
    lowered_parts = [part.lower() for part in path.parts]
    stem = path.stem.lower()

    if scanned_file.file_type == FileType.config or stem in {"config", "settings"}:
        return KnowledgeNodeType.config
    if _contains(lowered_parts, {"service", "services"}):
        return KnowledgeNodeType.service
    if _contains(lowered_parts, {"repository", "repositories", "repo", "repos"}):
        return KnowledgeNodeType.repository
    if _contains(lowered_parts, {"database", "databases", "db", "session", "sessions"}):
        return KnowledgeNodeType.database
    if _contains(lowered_parts, {"model", "models", "schema", "schemas"}):
        return KnowledgeNodeType.schema
    if scanned_file.file_type == FileType.python:
        return KnowledgeNodeType.file
    return KnowledgeNodeType.unknown


def detect_class_node_type(file_path: str, class_info: ClassInfo) -> KnowledgeNodeType:
    if any(base.endswith("BaseModel") or base == "BaseModel" for base in class_info.base_classes):
        return KnowledgeNodeType.request_model
    lowered_parts = [part.lower() for part in PurePosixPath(file_path).parts]
    if _contains(lowered_parts, {"model", "models", "schema", "schemas"}):
        return KnowledgeNodeType.schema
    return KnowledgeNodeType.class_


def _contains(values: list[str], options: set[str]) -> bool:
    return any(value in options for value in values)


def _file_id(file_path: str) -> str:
    return f"file:{file_path}"


def _route_id(path: str, method: str) -> str:
    return f"route:{method.upper()}:{path}"


def _function_id(file_path: str, function_name: str) -> str:
    return f"function:{file_path}:{function_name}"


def _class_id(file_path: str, class_name: str) -> str:
    return f"class:{file_path}:{class_name}"


def _module_id(module: str) -> str:
    return f"module:{module}"
