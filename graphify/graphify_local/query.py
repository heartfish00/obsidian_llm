from __future__ import annotations

from collections import deque
import sqlite3
from typing import Any

DEFAULT_VISIBLE_KINDS = {"note", "note_ref", "topic", "type", "index"}


def quote_fts_query(query: str) -> str:
    tokens = [token.strip().replace('"', '') for token in query.split() if token.strip()]
    return " OR ".join(f'"{token}"' for token in tokens) if tokens else ""


def search_notes(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        rows = conn.execute(
            "SELECT id AS note_id, title, path, summary, 0.0 AS score FROM notes ORDER BY modified_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    fts_query = quote_fts_query(query)
    try:
        rows = conn.execute(
            """
            SELECT notes.id AS note_id, notes.title, notes.path, notes.summary,
                   bm25(note_fts) AS score
            FROM note_fts
            JOIN notes ON notes.id = note_fts.note_id
            WHERE note_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        like = f"%{query}%"
        rows = conn.execute(
            """
            SELECT id AS note_id, title, path, summary, 0.0 AS score
            FROM notes
            WHERE title LIKE ? OR summary LIKE ? OR frontmatter_json LIKE ?
            LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def neighbor_edges(conn: sqlite3.Connection, node_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT source_id, target_id, relation, provenance, confidence FROM edges WHERE source_id = ? OR target_id = ?",
        (node_id, node_id),
    ).fetchall()


def build_subgraph(conn: sqlite3.Connection, seed_note_ids: list[str], hops: int = 1, max_nodes: int = 120) -> dict[str, Any]:
    hops = max(1, min(2, hops))
    seen_nodes = set(seed_note_ids)
    seen_edges: set[tuple[str, str, str, str]] = set()
    queue = deque((node_id, 0) for node_id in seed_note_ids)

    while queue and len(seen_nodes) < max_nodes:
        node_id, depth = queue.popleft()
        if depth >= hops:
            continue
        for edge in neighbor_edges(conn, node_id):
            edge_key = (edge["source_id"], edge["target_id"], edge["relation"], edge["provenance"], edge["confidence"])
            seen_edges.add(edge_key)
            for candidate in (edge["source_id"], edge["target_id"]):
                if candidate not in seen_nodes and len(seen_nodes) < max_nodes:
                    seen_nodes.add(candidate)
                    queue.append((candidate, depth + 1))

    if seen_nodes and table_exists(conn, "node_metrics"):
        node_rows = conn.execute(
            f"""
            SELECT nodes.id, nodes.kind, nodes.label,
                   node_metrics.degree, node_metrics.in_degree, node_metrics.out_degree,
                   node_metrics.degree_centrality, node_metrics.pagerank,
                   node_metrics.component_id, node_metrics.component_size,
                   node_metrics.backend AS metrics_backend
            FROM nodes
            LEFT JOIN node_metrics ON node_metrics.node_id = nodes.id
            WHERE nodes.id IN ({','.join('?' for _ in seen_nodes)})
            """,
            tuple(seen_nodes),
        ).fetchall()
    elif seen_nodes:
        node_rows = conn.execute(
            f"SELECT id, kind, label FROM nodes WHERE id IN ({','.join('?' for _ in seen_nodes)})",
            tuple(seen_nodes),
        ).fetchall()
    else:
        node_rows = []
    nodes = []
    for row in node_rows:
        node = dict(row)
        node["seed"] = row["id"] in seed_note_ids
        node["metrics"] = {
            "degree": node.pop("degree", 0) or 0,
            "in_degree": node.pop("in_degree", 0) or 0,
            "out_degree": node.pop("out_degree", 0) or 0,
            "degree_centrality": node.pop("degree_centrality", 0.0) or 0.0,
            "pagerank": node.pop("pagerank", 0.0) or 0.0,
            "component_id": node.pop("component_id", 0) or 0,
            "component_size": node.pop("component_size", 1) or 1,
            "backend": node.pop("metrics_backend", "unavailable") or "unavailable",
        }
        nodes.append(node)
    apply_display_metadata(nodes)
    edges = [
        {"source": source, "target": target, "relation": relation, "provenance": provenance, "confidence": confidence}
        for source, target, relation, provenance, confidence in sorted(seen_edges)
        if source in seen_nodes and target in seen_nodes
    ]
    return {"nodes": nodes, "edges": edges, "seed_note_ids": seed_note_ids, "hops": hops, "metrics": graph_metrics_info(conn)}


def apply_display_metadata(nodes: list[dict[str, Any]]) -> None:
    visible_nodes = [
        node
        for node in nodes
        if bool(node.get("seed")) or node.get("kind") in DEFAULT_VISIBLE_KINDS
    ]
    ranked_nodes = sorted(visible_nodes, key=lambda node: (-display_score(node), node["kind"], node["label"], node["id"]))
    rank_by_id = {node["id"]: idx for idx, node in enumerate(ranked_nodes, 1)}
    for node in nodes:
        visible_by_default = bool(node.get("seed")) or node.get("kind") in DEFAULT_VISIBLE_KINDS
        node["display"] = {
            "score": display_score(node),
            "visible_by_default": visible_by_default,
            "rank": rank_by_id[node["id"]] if visible_by_default else None,
            "reason": "seed" if node.get("seed") else ("knowledge-node" if visible_by_default else "metadata-hidden"),
        }


def display_score(node: dict[str, Any]) -> float:
    metrics = node.get("metrics", {})
    pagerank = float(metrics.get("pagerank", 0.0) or 0.0)
    if pagerank > 0:
        return pagerank
    centrality = float(metrics.get("degree_centrality", 0.0) or 0.0)
    if centrality > 0:
        return centrality
    return float(metrics.get("degree", 0) or 0)


def query_graph(conn: sqlite3.Connection, query: str, limit: int = 10, hops: int = 1) -> dict[str, Any]:
    results = search_notes(conn, query, limit=limit)
    subgraph = build_subgraph(conn, [row["note_id"] for row in results], hops=hops)
    return {"query": query, "results": results, "graph": subgraph}


def graph_metrics_info(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        rows = conn.execute("SELECT key, value FROM graph_meta WHERE key IN ('metrics_backend', 'networkx_available')").fetchall()
    except sqlite3.OperationalError:
        return {"backend": "unavailable", "networkx_available": False}
    values = {row["key"]: row["value"] for row in rows}
    return {
        "backend": values.get("metrics_backend", "unavailable"),
        "networkx_available": values.get("networkx_available") == "true",
    }


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    return row is not None
