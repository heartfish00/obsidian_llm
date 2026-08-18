# Algorithm and safety notes

## Detection rules

- Treat a note as author-poor when normalized `author` input is missing, null, blank, or at most 2 visible characters. Read both `author` and legacy `authur`, but write only `author`.
- Build `core_shared_keywords` from normalized `keywords` / `tags` values that also appear as exact title tokens.
- When a note has no `keywords` or `tags` in frontmatter, automatically derive keywords from title tokens via `tokenize_title()`. This allows notes without explicit keywords to still participate in backlink matching.
- Build backlink candidates from shared `core_shared_keywords` plus shared normalized author values.
- Score backlink candidates by shared signal count, then by stable path ordering.
- Consider a backlink already present when the body already links the note by relative path or basename.

## Author reference matching (`--author-ref`)

- When `--author-ref` is provided, parse the specified reference note(s) and extract all author-like fields (keys containing "author" case-insensitively, including `AUTHOR:`, `author:`, `authur:`).
- Wikilink values like `[[Some Name]]` are unwrapped to `Some Name` for matching.
- For author-poor notes, attempt reference matching before domain fallback:
  1. **Exact body wikilink match**: if a note's body contains `[[케인]]` and the reference has author `케인`, match directly.
  2. **Token-overlap body wikilink match**: tokenize both the wikilink text and reference author name; if they share tokens, match (e.g., `[[케인]]` matches `모두의 AI 케인` via shared token `케인`).
  3. **Token-overlap title match**: tokenize the note title and reference author name; if they share tokens, match.
- Reference matching takes priority over domain-to-author fallback.

## Safety rules

- Use `ruamel.yaml` with quote preservation; do not replace it with PyYAML.
- Skip malformed YAML and continue.
- Modify only files that need changes.
- Preserve existing body text. Shared-block footers are merge-only: collapse duplicated `🔗 **Shared Keywords/Authors**` blocks into a single one, union links with dedup (normalized link keys), and drop self-referencing links. Repeated runs must be idempotent — a second pass proposes zero changes.
- Sync frontmatter `core_shared_keywords` to the computed title-backed keyword list.
- Normalize legacy `authur` into `author` without dropping existing non-link author values.
- Prefer `--mode preview` or a narrow `--path-glob` before broad runs.
- Keep preview output bounded with `--preview-link-limit` and `--preview-error-limit` on large vaults.

## Consolidation mode (`--consolidate-only`)

- Proposes only the merging of stacked duplicate shared blocks; computes no new backlinks and changes no metadata.
- Frontmatter is written back verbatim (no ruamel round-trip) so vault-wide cleanup diffs stay minimal.
- Block detection is format-tolerant (emoji variation selector, bold-marker drift, spacing, letter case) but only classifies a line as a block when what follows the label is empty or a wikilink, so prose that merely mentions "shared keywords" is never rewritten.

## Phase mapping

1. Bootstrap the skill scaffold and CLI entrypoint.
2. Implement vault scan, frontmatter parsing, and reverse index creation.
3. Implement orphan detection and deterministic fix proposals.
4. Implement interactive/apply modes and safe writes.
5. Validate with synthetic notes plus a narrow preview against the real vault.
