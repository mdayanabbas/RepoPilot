from backend.app.knowledge_graph.edge_builder import build_edges
from backend.app.knowledge_graph.node_builder import build_nodes
from backend.app.knowledge_graph.query import KnowledgeGraphQuery
from backend.app.schemas.architecture import ArchitectureGraph
from backend.app.schemas.intelligence import RouteIndex, SymbolIndex
from backend.app.schemas.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphSummary,
    KnowledgeNodeType,
)
from backend.app.schemas.retrieval import RetrievalResult
from backend.app.schemas.scan import ScanResult


class KnowledgeGraphService:
    def build_graph(
        self,
        *,
        scan_result: ScanResult,
        symbol_index: SymbolIndex,
        route_index: RouteIndex,
        architecture_graph: ArchitectureGraph | None = None,
        retrieval_result: RetrievalResult | None = None,
        issue_text: str | None = None,
    ) -> KnowledgeGraph:
        del architecture_graph
        nodes = build_nodes(
            scan_result=scan_result,
            symbol_index=symbol_index,
            route_index=route_index,
        )
        if retrieval_result is not None and retrieval_result.files:
            nodes.append(
                KnowledgeGraphNode(
                    id="issue:current",
                    type=KnowledgeNodeType.unknown,
                    label="Current issue",
                    metadata={"issue_length": len(issue_text or "")},
                )
            )
        edges = build_edges(
            scan_result=scan_result,
            symbol_index=symbol_index,
            route_index=route_index,
            retrieval_result=retrieval_result,
            issue_text=issue_text,
        )
        nodes = sorted(_dedupe_nodes(nodes).values(), key=lambda node: node.id)
        edges = sorted(edges, key=lambda edge: edge.id)
        return KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            summary=_summary(nodes, edges),
        )

    def query(self, graph: KnowledgeGraph) -> KnowledgeGraphQuery:
        return KnowledgeGraphQuery(graph)


def _dedupe_nodes(
    nodes: list[KnowledgeGraphNode],
) -> dict[str, KnowledgeGraphNode]:
    return {node.id: node for node in nodes}


def _summary(
    nodes: list[KnowledgeGraphNode],
    edges: list[KnowledgeGraphEdge],
) -> KnowledgeGraphSummary:
    return KnowledgeGraphSummary(
        total_nodes=len(nodes),
        total_edges=len(edges),
        route_count=_count(nodes, KnowledgeNodeType.route),
        handler_count=_count(nodes, KnowledgeNodeType.handler_function),
        model_count=(
            _count(nodes, KnowledgeNodeType.request_model)
            + _count(nodes, KnowledgeNodeType.response_model)
            + _count(nodes, KnowledgeNodeType.schema)
        ),
        service_count=_count(nodes, KnowledgeNodeType.service),
        database_node_count=_count(nodes, KnowledgeNodeType.database),
    )


def _count(nodes: list[KnowledgeGraphNode], node_type: KnowledgeNodeType) -> int:
    return sum(1 for node in nodes if node.type == node_type)
