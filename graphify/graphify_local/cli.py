from __future__ import annotations

import argparse
from pathlib import Path

from .db import build_database, connect
from .export import write_graph_html, write_json, write_query_markdown
from .query import query_graph


def cmd_build(args: argparse.Namespace) -> None:
    stats = build_database(Path(args.vault), Path(args.db), limit=args.limit, exclude_dirs=args.exclude_dir)
    print(f"built db={args.db} notes={stats['notes']} nodes={stats['nodes']} edges={stats['edges']}")


def cmd_query(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(Path(args.db))
    try:
        payload = query_graph(conn, args.query, limit=args.limit, hops=args.hops)
    finally:
        conn.close()
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
    query.set_defaults(func=cmd_query)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
