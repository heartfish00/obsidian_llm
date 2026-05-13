# Graphify Local Workflows

## Status first

Run `scripts/graphify_status.py` before querying when DB freshness or existence is uncertain.

## Rebuild

Use rebuild only when the user asks to build/rebuild/preprocess/update the graph DB, or when the default DB is missing. Full rebuild may take minutes. Use `--limit N` for quick partial validation.

## Query

Use query when the user asks to find notes, create a graph, or return an HTML path. Prefer `--hops 2` for exploration unless the user asks for a smaller graph. Return the HTML path plus the top note titles if useful.

## Safety

Do not commit generated DB or real-vault query outputs. Keep outputs under `graphify/output/`.
