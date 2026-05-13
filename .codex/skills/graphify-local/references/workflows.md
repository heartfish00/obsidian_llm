# Graphify Local Workflows

## Status first

Run `scripts/graphify_status.py` before querying when DB freshness or existence is uncertain.

## Rebuild

Use rebuild only when the user asks to build/rebuild/preprocess/update the graph DB, or when the default DB is missing. Full rebuild may take minutes. Use `--limit N` for quick partial validation.

## Query

Use query when the user asks to find notes, create a graph, or return an HTML path. Prefer `--hops 2` for exploration unless the user asks for a smaller graph. Return the HTML path plus the top note titles if useful.

Add `--search-x` when the user asks for Search X/X/Twitter/trends/realtime social context. Search X uses xAI Responses API `x_search` and requires `XAI_API_KEY` in the shell environment or repo root `.env`. Missing keys are recorded as `missing_api_key` in the generated result files, so the local graph query still completes.

Optional Search X filters:

- `--x-allowed-handles openai,xai`
- `--x-excluded-handles bots,spam`
- `--x-from-date YYYY-MM-DD`
- `--x-to-date YYYY-MM-DD`
- `--x-model grok-4.3`

## Safety

Do not commit generated DB or real-vault query outputs. Keep outputs under `graphify/output/`. Never hard-code `XAI_API_KEY`; read it from the environment or gitignored `.env`.
