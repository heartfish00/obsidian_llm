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
