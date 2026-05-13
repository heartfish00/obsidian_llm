#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path('/mnt/d/Program Files/Obsidian/graphify/output/full/vault_graph.sqlite')


def main() -> int:
    parser = argparse.ArgumentParser(description='Show Graphify Local DB status.')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    db = args.db
    if not db.exists():
        print(f'missing db: {db}')
        return 1
    print(f'db: {db.resolve()}')
    print(f'size_mb: {db.stat().st_size / 1024 / 1024:.2f}')
    print(f'modified: {datetime.fromtimestamp(db.stat().st_mtime).isoformat(timespec="seconds")}')
    conn = sqlite3.connect(db)
    try:
        for table in ('notes', 'nodes', 'edges', 'node_metrics'):
            try:
                count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                print(f'{table}: {count}')
            except sqlite3.OperationalError:
                print(f'{table}: missing')
        try:
            rows = conn.execute(
                "SELECT key, value FROM graph_meta WHERE key IN ('metrics_backend', 'networkx_available') ORDER BY key"
            ).fetchall()
            for key, value in rows:
                print(f'{key}: {value}')
        except sqlite3.OperationalError:
            print('graph_meta: missing')
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
