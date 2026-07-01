from backend.app.knowledge_graph.service import KnowledgeGraphService
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    PythonFileSymbols,
    RouteIndex,
    RouteInfo,
    SymbolIndex,
)
from backend.app.schemas.knowledge_graph import (
    KnowledgeEdgeType,
    KnowledgeGraph,
    KnowledgeNodeType,
)
from backend.app.schemas.scan import FileType, ScanResult, ScannedFile


def test_creates_route_nodes() -> None:
    graph = _graph()

    route = _node(graph, "route:POST:/api/login")

    assert route.type == KnowledgeNodeType.route
    assert route.label == "POST /api/login"


def test_creates_handler_function_nodes() -> None:
    graph = _graph()

    handler = _node(graph, "function:routes/auth.py:login")

    assert handler.type == KnowledgeNodeType.handler_function


def test_connects_route_to_handler() -> None:
    graph = _graph()

    assert _has_edge(
        graph,
        "route:POST:/api/login",
        "function:routes/auth.py:login",
        KnowledgeEdgeType.route_handled_by,
    )


def test_creates_class_model_nodes() -> None:
    graph = _graph()

    model = _node(graph, "class:schemas/auth.py:LoginRequest")

    assert model.type == KnowledgeNodeType.request_model
    assert graph.summary.model_count >= 1


def test_connects_handler_to_request_model() -> None:
    graph = _graph()

    assert _has_edge(
        graph,
        "function:routes/auth.py:login",
        "class:schemas/auth.py:LoginRequest",
        KnowledgeEdgeType.handler_uses_model,
    )


def test_creates_import_edges() -> None:
    graph = _graph()

    assert _has_edge(
        graph,
        "file:routes/auth.py",
        "module:services.auth_service",
        KnowledgeEdgeType.file_imports_module,
    )


def test_detects_service_repository_database_layers() -> None:
    graph = _graph()

    assert _node(graph, "file:services/auth_service.py").type == KnowledgeNodeType.service
    assert _node(graph, "file:repositories/user_repository.py").type == (
        KnowledgeNodeType.repository
    )
    assert _node(graph, "file:database/session.py").type == KnowledgeNodeType.database
    assert _has_edge(
        graph,
        "file:services/auth_service.py",
        "file:repositories/user_repository.py",
        KnowledgeEdgeType.service_uses_repository,
    )
    assert _has_edge(
        graph,
        "file:repositories/user_repository.py",
        "file:database/session.py",
        KnowledgeEdgeType.repository_uses_database,
    )


def test_route_neighborhood_returns_related_nodes() -> None:
    query = KnowledgeGraphService().query(_graph())

    neighborhood = query.get_route_neighborhood("/api/login", "POST")
    node_ids = {node.id for node in neighborhood.nodes}

    assert "route:POST:/api/login" in node_ids
    assert "function:routes/auth.py:login" in node_ids


def test_file_neighborhood_returns_related_nodes() -> None:
    query = KnowledgeGraphService().query(_graph())

    neighborhood = query.get_file_neighborhood("routes/auth.py")
    node_ids = {node.id for node in neighborhood.nodes}

    assert "file:routes/auth.py" in node_ids
    assert "module:services.auth_service" in node_ids
    assert "function:routes/auth.py:login" in node_ids


def test_output_is_deterministic() -> None:
    first = _graph()
    second = _graph()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def _graph() -> KnowledgeGraph:
    return KnowledgeGraphService().build_graph(
        scan_result=_scan(),
        symbol_index=_symbols(),
        route_index=_routes(),
    )


def _scan() -> ScanResult:
    files = [
        ScannedFile(path="main.py", file_type=FileType.python, size_bytes=100),
        ScannedFile(path="routes/auth.py", file_type=FileType.python, size_bytes=100),
        ScannedFile(path="schemas/auth.py", file_type=FileType.python, size_bytes=100),
        ScannedFile(
            path="services/auth_service.py",
            file_type=FileType.python,
            size_bytes=100,
        ),
        ScannedFile(
            path="repositories/user_repository.py",
            file_type=FileType.python,
            size_bytes=100,
        ),
        ScannedFile(
            path="database/session.py",
            file_type=FileType.python,
            size_bytes=100,
        ),
    ]
    return ScanResult(
        total_files=len(files),
        python_files=len(files),
        files=files,
    )


def _symbols() -> SymbolIndex:
    return SymbolIndex(
        files=[
            PythonFileSymbols(
                path="routes/auth.py",
                imports=[
                    ImportInfo(module="schemas.auth", name="LoginRequest"),
                    ImportInfo(module="services.auth_service", name="authenticate"),
                ],
                functions=[
                    FunctionInfo(
                        name="login",
                        line_number=8,
                        args=["login_request"],
                    )
                ],
            ),
            PythonFileSymbols(
                path="schemas/auth.py",
                imports=[ImportInfo(module="pydantic", name="BaseModel")],
                classes=[
                    ClassInfo(
                        name="LoginRequest",
                        line_number=4,
                        base_classes=["BaseModel"],
                    )
                ],
            ),
            PythonFileSymbols(
                path="services/auth_service.py",
                imports=[
                    ImportInfo(
                        module="repositories.user_repository",
                        name="get_user",
                    )
                ],
                functions=[
                    FunctionInfo(name="authenticate", line_number=3, args=["email"])
                ],
            ),
            PythonFileSymbols(
                path="repositories/user_repository.py",
                imports=[ImportInfo(module="database.session", name="get_db")],
                functions=[FunctionInfo(name="get_user", line_number=3, args=["email"])],
            ),
            PythonFileSymbols(
                path="database/session.py",
                imports=[],
                functions=[FunctionInfo(name="get_db", line_number=3)],
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
            )
        ]
    )


def _node(graph: KnowledgeGraph, node_id: str):
    return next(node for node in graph.nodes if node.id == node_id)


def _has_edge(
    graph: KnowledgeGraph,
    source: str,
    target: str,
    edge_type: KnowledgeEdgeType,
) -> bool:
    return any(
        edge.source == source and edge.target == target and edge.type == edge_type
        for edge in graph.edges
    )
