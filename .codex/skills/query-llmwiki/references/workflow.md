# Query workflow

## Core principles

- No RAG.
- No vector DB.
- No embeddings.
- No note mutation.
- Metadata first, long context second.

## Step 0 — Preflight

- Read only a small sample of notes if you need to confirm how frontmatter is populated.
- Keep the search root vault-wide unless the user explicitly asks for a narrower folder.
- Start with frontmatter plus the first 20 body lines.
- Skip obvious system and clutter folders on the first pass: `.codex`, `.git`, `.obsidian`, `.obsidian-terminal-env`, `.omc`, `.omx`, `.smart-connections`, `.smart-env`, `.smtcmp_chat_histories`, `.smtcmp_json_db`, `.trash`, `attachments`, `Templetes`, and `Templetes_keep(20250619)`.
- Re-include those folders only if the first pass is empty, the user explicitly points at them, or the remaining evidence is still too weak.
- Do not scan the whole vault body-by-body unless the narrowed candidate set still cannot answer the question.

## Step 1 — Route the question

- Convert the user question into:
  - `topics_filter`
  - `index_filter`
  - `authur_filter`
  - `tags_filter`
  - `text_query`
- Keep the filter set minimal and high-confidence.
- If the user names a title or entity directly, prepare at most 3 literal alias variants for retrieval, such as spacing changes, case changes, or a common spelling variant.

## Step 2 — Filter notes locally

- Parse frontmatter from local markdown notes.
- Normalize keys in memory by stripping a trailing colon if present.
- Match metadata using exact match or contains logic only.
- Suggested matching order:
  1. exact or near-exact title and filename match
  2. direct wiki-link target match
  3. `index_filter`
  4. `topics_filter`
  5. `authur_filter`
  6. `tags_filter`
  7. `text_query` on title, summary, and light metadata text
  8. body text search only on the narrowed candidate set
- Treat 0-byte files and blank stubs as weak candidates unless another note points to them as the only source handle.

## Step 3 — Build answer context

### Case A: 10 notes or fewer

- Use title, path, url, frontmatter, summary, and the first 20 body lines first.
- Open the full body only for the final 1-3 notes that provide the actual answer or citation evidence.

### Case B: more than 10 notes

- Use title + summary + url instead of full body.
- Prefer the note summary exactly as stored in frontmatter.
- If a note has no url, keep the title or path as the source handle.
- If the candidate set is still noisy, drop link-list notes, empty files, and weak stubs before opening any full bodies.

## Step 4 — Answer

- Answer only from the provided note context.
- Cite sources inline or at the end.
- Preferred sources:
  - note title
  - note path
  - url

## Zero-hit fallback

If the first pass returns no results:

1. Tell the user the strict filter set returned no notes.
2. Relax the weakest filter first.
3. Retry with `text_query` plus one strong metadata field.
4. Re-include the default-skipped folders if they are plausibly relevant.
5. Run body search only on the narrowed candidate set.
6. If still empty, say that relevant notes were not found.

## Hallucination guard

Use this instruction in the final answer stage:

```text
제공된 컨텍스트에 없는 내용은 절대 지어내지 말 것. 관련 노트에 해당 내용이 없으면 그렇게 명시할 것.
```

## Implementation notes

- Support both `topics` and `"topics:"` style keys when reading frontmatter.
- Preserve `authur` as-is, even if it looks misspelled.
- Prefer title/summary/url packing over clever ranking tricks.
- Prefer direct note evidence over external run memory for ordinary vault queries.
