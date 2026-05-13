#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path('/mnt/d/Program Files/Obsidian')
DEFAULT_VAULT = Path('/mnt/d/Sales Planning/obsidian/my')
DEFAULT_DB = DEFAULT_ROOT / 'graphify/output/full/vault_graph.sqlite'


def run(cmd: list[str], cwd: Path) -> int:
    print('+ ' + ' '.join(str(part) for part in cmd))
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    parser = argparse.ArgumentParser(description='Rebuild the Graphify Local SQLite/FTS DB.')
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--vault', type=Path, default=DEFAULT_VAULT)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--limit', type=int, default=None, help='Preprocess only the first N markdown files.')
    parser.add_argument('--exclude-dir', action='append', default=None, help='Extra/default directory name to exclude; repeatable.')
    args = parser.parse_args()

    cmd = [
        sys.executable,
        '-m',
        'graphify_local.cli',
        'build',
        '--vault',
        str(args.vault),
        '--db',
        str(args.db),
    ]
    if args.limit is not None:
        cmd.extend(['--limit', str(args.limit)])
    if args.exclude_dir:
        for value in args.exclude_dir:
            cmd.extend(['--exclude-dir', value])
    env = dict(**__import__('os').environ)
    env['PYTHONPATH'] = str(args.root / 'graphify') + (':' + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    print('+ ' + ' '.join(cmd))
    return subprocess.call(cmd, cwd=str(args.root), env=env)


if __name__ == '__main__':
    raise SystemExit(main())
