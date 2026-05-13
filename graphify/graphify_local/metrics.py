from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def compute_node_metrics(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute graph metrics with NetworkX when available, otherwise use a deterministic fallback.

    NetworkX is intentionally optional so the local, dependency-light MVP continues to work in
    offline vault environments. Installing `networkx` upgrades PageRank/centrality quality while
    keeping the same output shape.
    """
    try:
        import networkx as nx  # type: ignore
    except ImportError:
        metrics = _compute_fallback_metrics(nodes, edges)
        return {"backend": "fallback", "available": False, "metrics": metrics}

    directed = nx.DiGraph()
    for node in nodes:
        directed.add_node(node["id"])
    for edge in edges:
        source = edge["source_id"]
        target = edge["target_id"]
        if directed.has_edge(source, target):
            directed[source][target]["weight"] += 1.0
        else:
            directed.add_edge(source, target, weight=1.0)

    undirected = directed.to_undirected()
    pagerank = _safe_pagerank(nx, directed)
    degree_centrality = nx.degree_centrality(undirected) if directed.number_of_nodes() > 1 else {node: 0.0 for node in directed.nodes}
    components = _component_lookup(nx, undirected)

    metrics: dict[str, dict[str, Any]] = {}
    for node_id in directed.nodes:
        metrics[node_id] = {
            "degree": int(directed.in_degree(node_id) + directed.out_degree(node_id)),
            "in_degree": int(directed.in_degree(node_id)),
            "out_degree": int(directed.out_degree(node_id)),
            "degree_centrality": float(degree_centrality.get(node_id, 0.0)),
            "pagerank": float(pagerank.get(node_id, 0.0)),
            "component_id": components[node_id][0],
            "component_size": components[node_id][1],
            "backend": "networkx",
        }
    return {"backend": "networkx", "available": True, "metrics": metrics}


def _safe_pagerank(nx: Any, graph: Any) -> dict[str, float]:
    if graph.number_of_nodes() == 0:
        return {}
    try:
        return dict(nx.pagerank(graph, weight="weight"))
    except Exception:
        fallback_value = 1.0 / graph.number_of_nodes()
        return {node: fallback_value for node in graph.nodes}


def _component_lookup(nx: Any, graph: Any) -> dict[str, tuple[int, int]]:
    lookup: dict[str, tuple[int, int]] = {}
    components = sorted(nx.connected_components(graph), key=lambda component: (-len(component), sorted(component)[0] if component else ""))
    for component_id, component in enumerate(components):
        size = len(component)
        for node_id in component:
            lookup[node_id] = (component_id, size)
    return lookup


def _compute_fallback_metrics(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    node_ids = [node["id"] for node in nodes]
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, int] = defaultdict(int)
    neighbors: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        source = edge["source_id"]
        target = edge["target_id"]
        outgoing[source] += 1
        incoming[target] += 1
        neighbors.setdefault(source, set()).add(target)
        neighbors.setdefault(target, set()).add(source)

    components = _fallback_components(node_ids, neighbors)
    denominator = max(1, len(node_ids) - 1)
    metrics: dict[str, dict[str, Any]] = {}
    for node_id in node_ids:
        degree = incoming[node_id] + outgoing[node_id]
        metrics[node_id] = {
            "degree": degree,
            "in_degree": incoming[node_id],
            "out_degree": outgoing[node_id],
            "degree_centrality": degree / denominator,
            "pagerank": 0.0,
            "component_id": components[node_id][0],
            "component_size": components[node_id][1],
            "backend": "fallback",
        }
    return metrics


def _fallback_components(node_ids: list[str], neighbors: dict[str, set[str]]) -> dict[str, tuple[int, int]]:
    lookup: dict[str, tuple[int, int]] = {}
    visited: set[str] = set()
    component_id = 0
    for start in sorted(node_ids):
        if start in visited:
            continue
        component: list[str] = []
        queue: deque[str] = deque([start])
        visited.add(start)
        while queue:
            node_id = queue.popleft()
            component.append(node_id)
            for neighbor in sorted(neighbors.get(node_id, set())):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        for node_id in component:
            lookup[node_id] = (component_id, len(component))
        component_id += 1
    return lookup
