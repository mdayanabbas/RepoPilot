from pathlib import PurePosixPath

from backend.app.schemas.architecture import ArchitectureEdge, ArchitectureEdgeType
from backend.app.schemas.intelligence import SymbolIndex


def build_import_edges(symbol_index: SymbolIndex) -> list[ArchitectureEdge]:
    file_paths = {file_symbols.path for file_symbols in symbol_index.files}
    edges: list[ArchitectureEdge] = []

    for file_symbols in sorted(symbol_index.files, key=lambda item: item.path):
        source_id = file_node_id(file_symbols.path)
        for imported in sorted(
            file_symbols.imports,
            key=lambda item: (item.module, item.name or ""),
        ):
            module_name = imported.module.lstrip(".")
            target_file = _resolve_import_to_file(module_name, file_paths)
            target_id = (
                file_node_id(target_file) if target_file else module_node_id(module_name)
            )
            edges.append(
                ArchitectureEdge(
                    id=edge_id(source_id, target_id, ArchitectureEdgeType.imports),
                    source=source_id,
                    target=target_id,
                    type=ArchitectureEdgeType.imports,
                    metadata={
                        "module": imported.module,
                        "name": imported.name,
                    },
                )
            )
    return _dedupe_edges(edges)


def file_node_id(path: str) -> str:
    return f"file:{PurePosixPath(path).as_posix()}"


def module_node_id(module_name: str) -> str:
    return f"module:{module_name}"


def edge_id(
    source: str,
    target: str,
    edge_type: ArchitectureEdgeType,
) -> str:
    return f"{edge_type.value}:{source}->{target}"


def _resolve_import_to_file(module_name: str, file_paths: set[str]) -> str | None:
    if not module_name:
        return None
    module_path = module_name.replace(".", "/")
    candidates = {
        f"{module_path}.py",
        f"{module_path}/__init__.py",
        f"{PurePosixPath(module_path).name}.py",
    }
    for candidate in sorted(candidates):
        if candidate in file_paths:
            return candidate
    suffix = f"/{module_path}.py"
    for file_path in sorted(file_paths):
        if file_path.endswith(suffix):
            return file_path
    return None


def _dedupe_edges(edges: list[ArchitectureEdge]) -> list[ArchitectureEdge]:
    deduped = {edge.id: edge for edge in edges}
    return [deduped[key] for key in sorted(deduped)]
