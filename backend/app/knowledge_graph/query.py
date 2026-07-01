from backend.app.schemas.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNeighborhood,
    KnowledgeGraphNode,
    KnowledgeNodeType,
)


class KnowledgeGraphQuery:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def get_route_neighborhood(
        self,
        path: str,
        method: str | None = None,
    ) -> KnowledgeGraphNeighborhood:
        route_nodes = [
            node
            for node in self.graph.nodes
            if node.type == KnowledgeNodeType.route
            and _route_path(node) == path
            and (method is None or _route_method(node) == method.upper())
        ]
        return self._neighborhood({node.id for node in route_nodes})

    def get_file_neighborhood(self, file_path: str) -> KnowledgeGraphNeighborhood:
        return self._neighborhood({f"file:{file_path}"})

    def get_issue_neighborhood(
        self,
        issue_text: str,
        top_k: int = 10,
    ) -> KnowledgeGraphNeighborhood:
        terms = _terms(issue_text)
        scored_nodes = [
            (_node_score(node, terms), node)
            for node in self.graph.nodes
            if node.type != KnowledgeNodeType.unknown
        ]
        selected = [
            node.id
            for score, node in sorted(scored_nodes, key=lambda item: (-item[0], item[1].id))
            if score > 0
        ][:top_k]
        if not selected:
            selected = [
                edge.target
                for edge in self.graph.edges
                if edge.source == "issue:current"
            ][:top_k]
        return self._neighborhood(set(selected))

    def _neighborhood(self, seed_ids: set[str]) -> KnowledgeGraphNeighborhood:
        related_edges = [
            edge
            for edge in self.graph.edges
            if edge.source in seed_ids or edge.target in seed_ids
        ]
        node_ids = set(seed_ids)
        for edge in related_edges:
            node_ids.add(edge.source)
            node_ids.add(edge.target)
        return KnowledgeGraphNeighborhood(
            nodes=_sorted_nodes(
                [node for node in self.graph.nodes if node.id in node_ids]
            ),
            edges=_sorted_edges(related_edges),
        )


def _route_path(node: KnowledgeGraphNode) -> str | None:
    label_parts = node.label.split(" ", 1)
    return label_parts[1] if len(label_parts) == 2 else None


def _route_method(node: KnowledgeGraphNode) -> str | None:
    return node.label.split(" ", 1)[0].upper() if node.label else None


def _terms(text: str) -> set[str]:
    return {
        term
        for term in "".join(
            character.lower() if character.isalnum() else " " for character in text
        ).split()
        if len(term) > 2
    }


def _node_score(node: KnowledgeGraphNode, terms: set[str]) -> int:
    haystack = " ".join(
        [
            node.id,
            node.label,
            node.file_path or "",
            " ".join(str(value) for value in node.metadata.values()),
        ]
    ).lower()
    return sum(1 for term in terms if term in haystack)


def _sorted_nodes(nodes: list[KnowledgeGraphNode]) -> list[KnowledgeGraphNode]:
    return sorted(nodes, key=lambda node: node.id)


def _sorted_edges(edges: list[KnowledgeGraphEdge]) -> list[KnowledgeGraphEdge]:
    return sorted(edges, key=lambda edge: edge.id)
