import re

from backend.app.schemas.architecture import ArchitectureGraph

SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_]")


def export_architecture_graph_to_mermaid(graph: ArchitectureGraph) -> str:
    lines = ["graph TD"]
    for node in graph.nodes:
        lines.append(f"  {_safe_id(node.id)}[\"{_escape_label(node.label)}\"]")
    for edge in graph.edges:
        lines.append(
            "  "
            f"{_safe_id(edge.source)} -->|{_escape_label(edge.type.value)}| "
            f"{_safe_id(edge.target)}"
        )
    return "\n".join(lines)


def _safe_id(value: str) -> str:
    safe = SAFE_ID_PATTERN.sub("_", value)
    if not safe or safe[0].isdigit():
        return f"node_{safe}"
    return safe


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
