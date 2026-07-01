from backend.app.architecture.service import ArchitectureService
from backend.app.schemas.architecture import (
    ArchitectureEdgeType,
    ArchitectureGraph,
    ArchitectureNode,
    ArchitectureNodeType,
)
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import (
    FunctionInfo,
    ImportInfo,
    PythonFileSymbols,
    RouteIndex,
    RouteInfo,
    SymbolIndex,
)
from backend.app.schemas.scan import FileType, ScanResult, ScannedFile


def test_builds_file_nodes() -> None:
    graph = _graph()

    file_nodes = {node.id: node for node in graph.nodes if node.file_path}

    assert "file:main.py" in file_nodes
    assert file_nodes["file:main.py"].file_path == "main.py"


def test_builds_route_nodes() -> None:
    graph = _graph()

    route_nodes = [node for node in graph.nodes if node.type == ArchitectureNodeType.route]

    assert any(node.id == "route:POST:/api/login" for node in route_nodes)
    assert graph.summary.route_count == 1


def test_builds_import_edges() -> None:
    graph = _graph()

    import_edges = [edge for edge in graph.edges if edge.type == ArchitectureEdgeType.imports]

    assert any(
        edge.source == "file:routes/auth.py"
        and edge.target == "file:services/auth_service.py"
        for edge in import_edges
    )


def test_detects_service_layer() -> None:
    graph = _graph()

    service_node = _node(graph, "file:services/auth_service.py")

    assert service_node.type == ArchitectureNodeType.service
    assert "service" in graph.summary.detected_layers


def test_detects_database_layer() -> None:
    graph = _graph()

    database_node = _node(graph, "file:database/session.py")

    assert database_node.type == ArchitectureNodeType.database
    assert "database" in graph.summary.detected_layers


def test_creates_handles_route_edges() -> None:
    graph = _graph()

    assert any(
        edge.type == ArchitectureEdgeType.handles_route
        and edge.source == "file:routes/auth.py"
        and edge.target == "route:POST:/api/login"
        for edge in graph.edges
    )


def test_output_is_deterministic() -> None:
    first = _graph()
    second = _graph()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def _graph() -> ArchitectureGraph:
    return ArchitectureService().build_graph(
        scan_result=_scan(),
        symbol_index=_symbols(),
        route_index=_routes(),
    )


def _scan() -> ScanResult:
    files = [
        ScannedFile(path="main.py", file_type=FileType.python, size_bytes=100),
        ScannedFile(path="routes/auth.py", file_type=FileType.python, size_bytes=100),
        ScannedFile(
            path="services/auth_service.py",
            file_type=FileType.python,
            size_bytes=100,
        ),
        ScannedFile(
            path="database/session.py",
            file_type=FileType.python,
            size_bytes=100,
        ),
        ScannedFile(path="settings.py", file_type=FileType.config, size_bytes=100),
    ]
    return ScanResult(
        total_files=len(files),
        python_files=4,
        config_files=1,
        files=files,
    )


def _symbols() -> SymbolIndex:
    return SymbolIndex(
        files=[
            PythonFileSymbols(
                path="main.py",
                imports=[
                    ImportInfo(module="routes.auth"),
                    ImportInfo(module="settings"),
                ],
                functions=[],
            ),
            PythonFileSymbols(
                path="routes/auth.py",
                imports=[ImportInfo(module="services.auth_service")],
                functions=[FunctionInfo(name="login", line_number=8)],
            ),
            PythonFileSymbols(
                path="services/auth_service.py",
                imports=[ImportInfo(module="database.session")],
                functions=[FunctionInfo(name="authenticate", line_number=3)],
            ),
            PythonFileSymbols(
                path="database/session.py",
                imports=[],
                functions=[FunctionInfo(name="get_db", line_number=4)],
            ),
        ]
    )


def _routes() -> RouteIndex:
    return RouteIndex(
        routes=[
            RouteInfo(
                framework=SupportedFramework.fastapi,
                path="/api/login",
                method="POST",
                handler_name="login",
                file_path="routes/auth.py",
                line_number=8,
                router_name="router",
            )
        ]
    )


def _node(graph: ArchitectureGraph, node_id: str) -> ArchitectureNode:
    return next(node for node in graph.nodes if node.id == node_id)
