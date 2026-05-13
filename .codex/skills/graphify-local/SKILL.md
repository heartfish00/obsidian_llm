---
name: graphify-local
description: Build, inspect, and query the local Graphify-style Obsidian metadata graph database. Use when Codex needs to rebuild/preprocess the vault graph DB, check graph DB status, or search the Obsidian vault and return generated graph.html, graph.json, query-result.md, or query-result.json paths using the graphify local CLI.
---

# Graphify Local

Use this skill to operate the vault-local metadata graph tool under `graphify/`.

## Core workflow

1. Read `references/paths.md` when path defaults are needed.
2. Read `references/workflows.md` when deciding between status, rebuild, and query.
3. Use bundled scripts instead of rewriting shell commands:
   - `scripts/graphify_status.py` checks DB existence, size, mtime, and counts.
   - `scripts/graphify_build.py` rebuilds the SQLite/FTS DB.
   - `scripts/graphify_query.py` queries the DB and prints output paths.

## Decision rules

- If the user asks to “build”, “rebuild”, “전처리”, “update DB”, or says the DB may be stale, run status first, then rebuild.
- If the user asks to “find”, “search”, “query”, “그래피파이로 찾아줘”, or asks for an HTML graph path, query the existing DB.
- If the default DB is missing, rebuild before querying unless the user explicitly forbids it.
- Use full DB by default: `graphify/output/full/vault_graph.sqlite`.
- Use `--limit N` only for tests, quick validation, or when the user asks for partial preprocessing.
- Use `--hops 2` by default for exploration; use `--hops 1` only for a smaller/noise-controlled graph.
- Keep generated outputs under `graphify/output/`; never stage DB or real-vault output files.

## Commands

Status:

```bash
.codex/skills/graphify-local/scripts/graphify_status.py
```

Full rebuild:

```bash
.codex/skills/graphify-local/scripts/graphify_build.py
```

Partial rebuild:

```bash
.codex/skills/graphify-local/scripts/graphify_build.py --limit 500 --db graphify/output/subset/vault_graph.sqlite
```

Query:

```bash
.codex/skills/graphify-local/scripts/graphify_query.py --query "codex context window" --hops 2
```

## Output response

For query tasks, return:

- `graph.html` absolute path
- `query-result.md` path
- top 3-5 note titles when helpful
- whether the DB was reused or rebuilt

For rebuild tasks, return notes/nodes/edges counts and DB path.
