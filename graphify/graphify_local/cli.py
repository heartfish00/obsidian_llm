from __future__ import annotations

import argparse
from pathlib import Path

from .db import build_database, connect
from .export import write_graph_html, write_json, write_query_markdown
from .query import query_graph
from .search_x import attach_x_search_context, search_x_posts, split_handles


def cmd_build(args: argparse.Namespace) -> None:
    stats = build_database(Path(args.vault), Path(args.db), limit=args.limit, exclude_dirs=args.exclude_dir)
    print(
        f"built db={args.db} notes={stats['notes']} nodes={stats['nodes']} edges={stats['edges']} "
        f"node_metrics={stats['node_metrics']} metrics_backend={stats['metrics_backend']}"
    )


def cmd_query(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(Path(args.db))
    try:
        payload = query_graph(conn, args.query, limit=args.limit, hops=args.hops)
    finally:
        conn.close()
    if args.search_x:
        x_payload = search_x_posts(
            args.query,
            model=args.x_model,
            allowed_handles=split_handles(args.x_allowed_handles),
            excluded_handles=split_handles(args.x_excluded_handles),
            from_date=args.x_from_date,
            to_date=args.x_to_date,
            timeout=args.x_timeout,
        )
        payload = attach_x_search_context(payload, x_payload)
    write_json(out_dir / "query-result.json", payload)
    write_json(out_dir / "graph.json", payload["graph"])
    write_query_markdown(out_dir / "query-result.md", payload)
    write_graph_html(out_dir / "graph.html", payload)
    print(f"wrote {out_dir / 'graph.json'} {out_dir / 'graph.html'} {out_dir / 'query-result.md'} {out_dir / 'query-result.json'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Metadata-only Obsidian graph search MVP")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Build SQLite graph/search database from a vault")
    build.add_argument("--vault", required=True)
    build.add_argument("--db", required=True)
    build.add_argument("--limit", type=int, default=None, help="Maximum number of Markdown notes to preprocess")
    build.add_argument(
        "--exclude-dir",
        action="append",
        default=[".git", ".obsidian", ".omx", ".trash", ".pytest_cache", "graphify"],
        help="Directory name to skip while scanning; repeatable",
    )
    build.set_defaults(func=cmd_build)

    query = sub.add_parser("query", help="Search and export a focused graph")
    query.add_argument("--db", required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--out-dir", required=True)
    query.add_argument("--limit", type=int, default=10)
    query.add_argument("--hops", type=int, choices=[1, 2], default=1)
    query.add_argument("--search-x", action="store_true", help="Augment local graph results with xAI Responses API x_search.")
    query.add_argument("--x-model", default=None, help="xAI model for Search X; defaults to SEARCH_X_MODEL or grok-4.3.")
    query.add_argument("--x-allowed-handles", default=None, help="Comma-separated X handles to include; max 10.")
    query.add_argument("--x-excluded-handles", default=None, help="Comma-separated X handles to exclude; max 10.")
    query.add_argument("--x-from-date", default=None, help="Search X start date in YYYY-MM-DD format.")
    query.add_argument("--x-to-date", default=None, help="Search X end date in YYYY-MM-DD format.")
    query.add_argument("--x-timeout", type=int, default=60, help="Search X HTTP timeout in seconds.")
    query.set_defaults(func=cmd_query)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
