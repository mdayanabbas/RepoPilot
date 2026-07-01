from pathlib import PurePosixPath

from backend.app.architecture.dependency_graph import (
    edge_id,
    file_node_id,
)
from backend.app.architecture.layer_detector import detect_file_layer, is_entrypoint
from backend.app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureEdgeType,
    ArchitectureGraph,
    ArchitectureNode,
    ArchitectureNodeType,
    ArchitectureSummary,
)
from backend.app.schemas.intelligence import RouteIndex, SymbolIndex
from backend.app.schemas.scan import ScanResult


def build_architecture_graph(
    scan_result: ScanResult,
    symbol_index: SymbolIndex,
    route_index: RouteIndex,
    import_edges: list[ArchitectureEdge],
) -> ArchitectureGraph:
    nodes: dict[str, ArchitectureNode] = {}
    edges: dict[str, ArchitectureEdge] = {}

    for scanned_file in sorted(scan_result.files, key=lambda item: item.path):
        layer = detect_file_layer(scanned_file)
        node_id = file_node_id(scanned_file.path)
        nodes[node_id] = ArchitectureNode(
            id=node_id,
            type=layer,
            label=PurePosixPath(scanned_file.path).name,
            file_path=PurePosixPath(scanned_file.path).as_posix(),
            metadata={"layer": layer.value, "file_type": scanned_file.file_type.value},
        )

    for file_symbols in sorted(symbol_index.files, key=lambda item: item.path):
        file_id = file_node_id(file_symbols.path)
        nodes.setdefault(
            file_id,
            ArchitectureNode(
                id=file_id,
                type=ArchitectureNodeType.file,
                label=PurePosixPath(file_symbols.path).name,
                file_path=file_symbols.path,
            ),
        )
        for function in sorted(file_symbols.functions, key=lambda item: item.name):
            function_id = f"function:{file_symbols.path}:{function.name}"
            nodes[function_id] = ArchitectureNode(
                id=function_id,
                type=ArchitectureNodeType.function,
                label=function.name,
                file_path=file_symbols.path,
                metadata={"line_number": function.line_number},
            )
            _add_edge(edges, file_id, function_id, ArchitectureEdgeType.defines)
        for class_info in sorted(file_symbols.classes, key=lambda item: item.name):
            class_id = f"class:{file_symbols.path}:{class_info.name}"
            nodes[class_id] = ArchitectureNode(
                id=class_id,
                type=ArchitectureNodeType.class_,
                label=class_info.name,
                file_path=file_symbols.path,
                metadata={"line_number": class_info.line_number},
            )
            _add_edge(edges, file_id, class_id, ArchitectureEdgeType.defines)

    for route in sorted(
        route_index.routes,
        key=lambda item: (item.file_path, item.path, item.method),
    ):
        route_id = f"route:{route.method}:{route.path}"
        file_id = file_node_id(route.file_path)
        nodes[route_id] = ArchitectureNode(
            id=route_id,
            type=ArchitectureNodeType.route,
            label=f"{route.method} {route.path}",
            file_path=route.file_path,
            metadata={
                "handler_name": route.handler_name,
                "line_number": route.line_number,
            },
        )
        _add_edge(edges, file_id, route_id, ArchitectureEdgeType.handles_route)

    for import_edge in import_edges:
        if import_edge.target.startswith("module:"):
            module_name = import_edge.target.removeprefix("module:")
            nodes.setdefault(
                import_edge.target,
                ArchitectureNode(
                    id=import_edge.target,
                    type=ArchitectureNodeType.module,
                    label=module_name,
                ),
            )
        edges[import_edge.id] = import_edge

    _add_layer_edges(nodes, edges)
    sorted_nodes = [nodes[key] for key in sorted(nodes)]
    sorted_edges = [edges[key] for key in sorted(edges)]
    return ArchitectureGraph(
        nodes=sorted_nodes,
        edges=sorted_edges,
        summary=ArchitectureSummary(
            total_nodes=len(sorted_nodes),
            total_edges=len(sorted_edges),
            detected_layers=sorted(
                {
                    node.type.value
                    for node in sorted_nodes
                    if node.file_path is not None
                    and node.type != ArchitectureNodeType.unknown
                }
            ),
            entrypoints=sorted(
                scanned_file.path
                for scanned_file in scan_result.files
                if is_entrypoint(scanned_file)
            ),
            route_count=len(route_index.routes),
        ),
    )


def _add_layer_edges(
    nodes: dict[str, ArchitectureNode],
    edges: dict[str, ArchitectureEdge],
) -> None:
    file_nodes = [node for node in nodes.values() if node.file_path is not None]
    database_nodes = [
        node for node in file_nodes if node.type == ArchitectureNodeType.database
    ]
    config_nodes = [
        node for node in file_nodes if node.type == ArchitectureNodeType.config
    ]
    service_nodes = [
        node for node in file_nodes if node.type == ArchitectureNodeType.service
    ]
    for node in file_nodes:
        if node.type == ArchitectureNodeType.service:
            for database_node in database_nodes:
                _add_edge(
                    edges,
                    node.id,
                    database_node.id,
                    ArchitectureEdgeType.uses_database,
                )
        if node.type == ArchitectureNodeType.file:
            for config_node in config_nodes:
                _add_edge(edges, node.id, config_node.id, ArchitectureEdgeType.configures)
        if node.type == ArchitectureNodeType.route:
            for service_node in service_nodes:
                _add_edge(
                    edges,
                    node.id,
                    service_node.id,
                    ArchitectureEdgeType.likely_depends_on,
                )


def _add_edge(
    edges: dict[str, ArchitectureEdge],
    source: str,
    target: str,
    edge_type: ArchitectureEdgeType,
) -> None:
    edge = ArchitectureEdge(
        id=edge_id(source, target, edge_type),
        source=source,
        target=target,
        type=edge_type,
    )
    edges.setdefault(edge.id, edge)
