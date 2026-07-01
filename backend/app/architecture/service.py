from backend.app.architecture.architecture_graph import build_architecture_graph
from backend.app.architecture.dependency_graph import build_import_edges
from backend.app.schemas.architecture import ArchitectureGraph
from backend.app.schemas.intelligence import RouteIndex, SymbolIndex
from backend.app.schemas.scan import ScanResult


class ArchitectureService:
    def build_graph(
        self,
        *,
        scan_result: ScanResult,
        symbol_index: SymbolIndex,
        route_index: RouteIndex,
    ) -> ArchitectureGraph:
        return build_architecture_graph(
            scan_result=scan_result,
            symbol_index=symbol_index,
            route_index=route_index,
            import_edges=build_import_edges(symbol_index),
        )
