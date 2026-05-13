#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path('/mnt/d/Program Files/Obsidian')
DEFAULT_DB = DEFAULT_ROOT / 'graphify/output/full/vault_graph.sqlite'


def slugify(value: str) -> str:
    slug = re.sub(r'[^0-9A-Za-z가-힣._-]+', '-', value.strip()).strip('-')
    return slug[:80] or 'query'


def main() -> int:
    parser = argparse.ArgumentParser(description='Query Graphify Local DB and export graph/context files.')
    parser.add_argument('--query', required=True)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--out-dir', type=Path, default=None)
    parser.add_argument('--hops', type=int, choices=[1, 2], default=2)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--search-x', action='store_true', help='Augment query output with xAI Responses API x_search.')
    parser.add_argument('--x-model', default=None, help='xAI model for Search X; defaults to SEARCH_X_MODEL or grok-4.3.')
    parser.add_argument('--x-allowed-handles', default=None, help='Comma-separated X handles to include; max 10.')
    parser.add_argument('--x-excluded-handles', default=None, help='Comma-separated X handles to exclude; max 10.')
    parser.add_argument('--x-from-date', default=None, help='Search X start date in YYYY-MM-DD format.')
    parser.add_argument('--x-to-date', default=None, help='Search X end date in YYYY-MM-DD format.')
    parser.add_argument('--x-timeout', type=int, default=60, help='Search X HTTP timeout in seconds.')
    args = parser.parse_args()

    out_dir = args.out_dir or (args.root / 'graphify/output' / slugify(args.query))
    cmd = [
        sys.executable,
        '-m',
        'graphify_local.cli',
        'query',
        '--db',
        str(args.db),
        '--query',
        args.query,
        '--hops',
        str(args.hops),
        '--limit',
        str(args.limit),
        '--out-dir',
        str(out_dir),
    ]
    if args.search_x:
        cmd.append('--search-x')
    for flag, value in [
        ('--x-model', args.x_model),
        ('--x-allowed-handles', args.x_allowed_handles),
        ('--x-excluded-handles', args.x_excluded_handles),
        ('--x-from-date', args.x_from_date),
        ('--x-to-date', args.x_to_date),
    ]:
        if value:
            cmd.extend([flag, value])
    if args.x_timeout != 60:
        cmd.extend(['--x-timeout', str(args.x_timeout)])
    env = dict(**os.environ)
    env['PYTHONPATH'] = str(args.root / 'graphify') + (':' + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    print('+ ' + ' '.join(cmd))
    code = subprocess.call(cmd, cwd=str(args.root), env=env)
    if code == 0:
        print(f'HTML: {(out_dir / "graph.html").resolve()}')
        print(f'Markdown: {(out_dir / "query-result.md").resolve()}')
        print(f'JSON: {(out_dir / "query-result.json").resolve()}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
