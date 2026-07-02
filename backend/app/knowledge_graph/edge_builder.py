from pathlib import PurePosixPath

from backend.app.knowledge_graph.node_builder import (
    detect_file_node_type,
)
from backend.app.schemas.intelligence import (
    ClassInfo,
    FunctionInfo,
    PythonFileSymbols,
    RouteIndex,
    SymbolIndex,
)
from backend.app.schemas.knowledge_graph import (
    KnowledgeEdgeType,
    KnowledgeGraphEdge,
    KnowledgeNodeType,
)
from backend.app.schemas.retrieval import RetrievalResult
from backend.app.schemas.scan import ScanResult, ScannedFile


def build_edges(
    *,
    scan_result: ScanResult,
    symbol_index: SymbolIndex,
    route_index: RouteIndex,
    retrieval_result: RetrievalResult | None = None,
    issue_text: str | None = None,
) -> list[KnowledgeGraphEdge]:
    del issue_text
    edges: dict[str, KnowledgeGraphEdge] = {}
    files_by_path = {file.path: file for file in scan_result.files}
    symbols_by_path = {file.path: file for file in symbol_index.files}
    module_to_file = _module_file_map(scan_result)
    model_classes = _model_classes(symbol_index)

    for file_symbols in symbol_index.files:
        file_id = _file_id(file_symbols.path)
        for imported in file_symbols.imports:
            _add_edge(
                edges,
                file_id,
                _module_id(imported.module),
                KnowledgeEdgeType.file_imports_module,
                {"module": imported.module, "name": imported.name},
            )
            imported_file = module_to_file.get(imported.module)
            if imported_file is not None:
                dependency_type = _dependency_edge_type(
                    source=files_by_path.get(file_symbols.path),
                    target=files_by_path.get(imported_file),
                )
                source_id = file_id
                target_id = _file_id(imported_file)
                if dependency_type == KnowledgeEdgeType.config_used_by:
                    source_id = _file_id(imported_file)
                    target_id = file_id
                _add_edge(
                    edges,
                    source_id,
                    target_id,
                    dependency_type,
                    {"module": imported.module},
                )

        for function in file_symbols.functions:
            _add_edge(
                edges,
                file_id,
                _function_id(file_symbols.path, function.name),
                KnowledgeEdgeType.file_defines_function,
                {"line_number": function.line_number},
            )
        for class_info in file_symbols.classes:
            _add_edge(
                edges,
                file_id,
                _class_id(file_symbols.path, class_info.name),
                KnowledgeEdgeType.file_defines_class,
                {"line_number": class_info.line_number},
            )

    for route in route_index.routes:
        handler_id = _function_id(route.file_path, route.handler_name)
        _add_edge(
            edges,
            _route_id(route.path, route.method),
            handler_id,
            KnowledgeEdgeType.route_handled_by,
            {"file_path": route.file_path, "line_number": route.line_number},
        )

        handler = _find_function(symbols_by_path.get(route.file_path), route.handler_name)
        if handler is not None:
            for class_path, class_info in _handler_models(handler, model_classes):
                _add_edge(
                    edges,
                    handler_id,
                    _class_id(class_path, class_info.name),
                    KnowledgeEdgeType.handler_uses_model,
                    {"model_name": class_info.name},
                )
            for target_path, target_function in _likely_called_functions(
                route.file_path,
                symbols_by_path,
                module_to_file,
            ):
                _add_edge(
                    edges,
                    handler_id,
                    _function_id(target_path, target_function.name),
                    KnowledgeEdgeType.handler_likely_calls,
                    {"via_file": target_path},
                )

    if retrieval_result is not None:
        for file in retrieval_result.files:
            if file.file_path in files_by_path:
                _add_edge(
                    edges,
                    _issue_id(),
                    _file_id(file.file_path),
                    KnowledgeEdgeType.related_to_issue,
                    {
                        "score": file.score,
                        "reason": file.reason,
                        "matched_signals": file.matched_signals,
                    },
                )

    return sorted(edges.values(), key=lambda edge: edge.id)


def _dependency_edge_type(
    *,
    source: ScannedFile | None,
    target: ScannedFile | None,
) -> KnowledgeEdgeType:
    if source is None or target is None:
        return KnowledgeEdgeType.file_likely_depends_on
    source_type = detect_file_node_type(source)
    target_type = detect_file_node_type(target)
    if source_type == KnowledgeNodeType.service and target_type == KnowledgeNodeType.repository:
        return KnowledgeEdgeType.service_uses_repository
    if source_type == KnowledgeNodeType.repository and target_type == KnowledgeNodeType.database:
        return KnowledgeEdgeType.repository_uses_database
    if target_type == KnowledgeNodeType.config:
        return KnowledgeEdgeType.config_used_by
    return KnowledgeEdgeType.file_likely_depends_on


def _module_file_map(scan_result: ScanResult) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for scanned_file in scan_result.files:
        path = PurePosixPath(scanned_file.path)
        if path.suffix != ".py":
            continue
        module = ".".join(path.with_suffix("").parts)
        mapping[module] = scanned_file.path
        if path.name == "__init__.py":
            mapping[".".join(path.parent.parts)] = scanned_file.path
    return mapping


def _model_classes(symbol_index: SymbolIndex) -> list[tuple[str, ClassInfo]]:
    models: list[tuple[str, ClassInfo]] = []
    for file_symbols in symbol_index.files:
        for class_info in file_symbols.classes:
            lowered_parts = [part.lower() for part in PurePosixPath(file_symbols.path).parts]
            is_pydantic = any(
                base.endswith("BaseModel") or base == "BaseModel"
                for base in class_info.base_classes
            )
            if is_pydantic or any(part in {"model", "models", "schema", "schemas"} for part in lowered_parts):
                models.append((file_symbols.path, class_info))
    return sorted(models, key=lambda item: (item[0], item[1].name))


def _handler_models(
    handler: FunctionInfo,
    models: list[tuple[str, ClassInfo]],
) -> list[tuple[str, ClassInfo]]:
    normalized_args = {_normalize(arg) for arg in handler.args}
    return [
        (file_path, class_info)
        for file_path, class_info in models
        if _normalize(class_info.name) in normalized_args
    ]


def _likely_called_functions(
    handler_file_path: str,
    symbols_by_path: dict[str, PythonFileSymbols],
    module_to_file: dict[str, str],
) -> list[tuple[str, FunctionInfo]]:
    file_symbols = symbols_by_path.get(handler_file_path)
    if file_symbols is None:
        return []
    imported_paths = [
        module_to_file[imported.module]
        for imported in file_symbols.imports
        if imported.module in module_to_file
    ]
    calls: list[tuple[str, FunctionInfo]] = []
    for imported_path in sorted(set(imported_paths)):
        imported_symbols = symbols_by_path.get(imported_path)
        if imported_symbols is None:
            continue
        calls.extend((imported_path, function) for function in imported_symbols.functions)
    return sorted(calls, key=lambda item: (item[0], item[1].name))


def _find_function(
    file_symbols: PythonFileSymbols | None,
    function_name: str,
) -> FunctionInfo | None:
    if file_symbols is None:
        return None
    return next(
        (function for function in file_symbols.functions if function.name == function_name),
        None,
    )


def _add_edge(
    edges: dict[str, KnowledgeGraphEdge],
    source: str,
    target: str,
    edge_type: KnowledgeEdgeType,
    metadata: dict[str, object] | None = None,
) -> None:
    edge_id = f"{edge_type.value}:{source}->{target}"
    edges[edge_id] = KnowledgeGraphEdge(
        id=edge_id,
        source=source,
        target=target,
        type=edge_type,
        metadata=metadata or {},
    )


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


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


def _issue_id() -> str:
    return "issue:current"
