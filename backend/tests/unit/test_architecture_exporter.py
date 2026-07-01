from backend.app.architecture.graph_exporter import export_architecture_graph_to_mermaid
from backend.app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureEdgeType,
    ArchitectureGraph,
    ArchitectureNode,
    ArchitectureNodeType,
    ArchitectureSummary,
)


def test_mermaid_exporter_creates_graph_td() -> None:
    mermaid = export_architecture_graph_to_mermaid(_graph())

    assert mermaid.startswith("graph TD")


def test_mermaid_exporter_includes_nodes_and_edges() -> None:
    mermaid = export_architecture_graph_to_mermaid(_graph())

    assert 'file_main_py["main.py"]' in mermaid
    assert 'route_GET__health["GET /health"]' in mermaid
    assert "file_main_py -->|handles_route| route_GET__health" in mermaid


def _graph() -> ArchitectureGraph:
    return ArchitectureGraph(
        nodes=[
            ArchitectureNode(
                id="file:main.py",
                type=ArchitectureNodeType.file,
                label="main.py",
                file_path="main.py",
            ),
            ArchitectureNode(
                id="route:GET:/health",
                type=ArchitectureNodeType.route,
                label="GET /health",
                file_path="main.py",
            ),
        ],
        edges=[
            ArchitectureEdge(
                id="handles_route:file:main.py->route:GET:/health",
                source="file:main.py",
                target="route:GET:/health",
                type=ArchitectureEdgeType.handles_route,
            )
        ],
        summary=ArchitectureSummary(
            total_nodes=2,
            total_edges=1,
            detected_layers=["file", "route"],
            entrypoints=["main.py"],
            route_count=1,
        ),
    )
