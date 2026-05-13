from __future__ import annotations

from collections import deque
import sqlite3
from typing import Any


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

    node_rows = conn.execute(
        f"SELECT id, kind, label FROM nodes WHERE id IN ({','.join('?' for _ in seen_nodes)})",
        tuple(seen_nodes),
    ).fetchall() if seen_nodes else []
    nodes = []
    for row in node_rows:
        node = dict(row)
        node["seed"] = row["id"] in seed_note_ids
        nodes.append(node)
    edges = [
        {"source": source, "target": target, "relation": relation, "provenance": provenance, "confidence": confidence}
        for source, target, relation, provenance, confidence in sorted(seen_edges)
        if source in seen_nodes and target in seen_nodes
    ]
    return {"nodes": nodes, "edges": edges, "seed_note_ids": seed_note_ids, "hops": hops}


def query_graph(conn: sqlite3.Connection, query: str, limit: int = 10, hops: int = 1) -> dict[str, Any]:
    results = search_notes(conn, query, limit=limit)
    subgraph = build_subgraph(conn, [row["note_id"] for row in results], hops=hops)
    return {"query": query, "results": results, "graph": subgraph}
