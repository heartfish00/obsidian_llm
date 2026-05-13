---
name: query-llmwiki
description: Answer questions over an Obsidian vault by routing through frontmatter metadata first, without embeddings, vector databases, or RAG infrastructure. Use when Codex needs to (1) map a user question to allowed Obsidian metadata filters such as topics, index, type, authur, and tags, (2) narrow candidate notes before long-context synthesis, or (3) plan or implement a metadata-first local query workflow that must preserve existing notes unchanged.
---

# Query LLMWiki

## Overview

Use this skill to turn a natural-language question into a metadata-first Obsidian search workflow, then answer only from the narrowed note set with explicit sources.

## Workflow

1. Read `references/taxonomy.md` before selecting any metadata filters.
2. Read `references/router-contract.md` before producing a router JSON object or tool-call schema.
3. Read `references/workflow.md` before deciding how much note content to load.
4. Read `references/prompt-examples.md` when you need concrete query-to-filter examples.

## Operating rules

- Use metadata first. Do not start with full-text body search unless metadata is too weak.
- Do not invent taxonomy values. Choose only from allowed values or from the user’s exact free-text intent where the contract permits it.
- Keep the search root vault-wide by default. Do not hard-scope retrieval to a single PARA area unless the user explicitly asks for that narrower scope.
- Treat the current vault format as authoritative:
  - many fields are stored with trailing colons such as `"topics:"`, `"index:"`, `"mode:"`, `"status:"`, `"date:"`, `"summary:"`
  - `tags` is usually stored without the trailing colon
- Normalize keys in memory if you are writing code or reasoning about filters, but do not rewrite existing notes just to make the schema prettier.
- Start with a low-noise pass that skips obvious system and clutter folders such as `.codex`, `.git`, `.obsidian`, `.obsidian-terminal-env`, `.omc`, `.omx`, `.smart-connections`, `.smart-env`, `.smtcmp_chat_histories`, `.smtcmp_json_db`, `.trash`, `attachments`, `Templetes`, and `Templetes_keep(20250619)`.
- Treat those folder skips as a default, not a permanent ban. Re-include them if the first pass returns zero notes, if the user explicitly names one of those areas, or if you still do not have enough evidence after the first pass.
- Read only a few sample notes, and prefer frontmatter plus the first 20 body lines until you know which notes are truly needed.
- When the user names an entity or note title, try only a small number of literal alias variants first, such as spacing or common spelling variants. Do not jump directly to broad substring scans.
- Keep the vault unchanged. This skill is for retrieval and routing, not bulk metadata cleanup.
- Do not read external memory files such as `MEMORY.md` for ordinary vault retrieval. Use them only when the user explicitly asks for prior-run context or cross-repo history.

## Context strategy

- If the filtered result set is small, start with title, frontmatter, summary, and the first 20 body lines.
- If the filtered result set is large, switch to title + summary + url packing before asking the final model to answer.
- Prefer `summary` over raw body text when the question is broad, the hit count is high, or the token budget is uncertain.
- Open full note bodies only for the final 1-3 notes that actually carry the answer or the citation evidence.
- Treat empty files, 0-byte files, and pure link-list notes as supporting signals unless they contain the only available evidence.

## Fallback behavior

- If the first pass returns zero notes, relax the query in a controlled order:
  1. keep `index` or `topics` only if they are high-confidence
  2. drop the weakest filter
  3. fall back to `text_query` plus a narrower metadata subset
  4. re-include the default-skipped folders if they are plausibly relevant
  5. only then use body search on the narrowed candidate set
- If the available notes still do not support the answer, say so plainly. Do not hallucinate missing facts.

## Output expectations

- Return the chosen filters in the router contract shape when the task is routing or implementation planning.
- Return the final answer with note-title or URL sources when the task is question answering.
- If the user asks for an implementation plan or script, preserve the same metadata-first contract instead of switching to RAG.
- 응답은 항상 마크다운 불렛 포인트로 작성할 것.
- 모든 항목에 출처 노트를 `[[노트파일명]]` (옵시디언 위키링크, .md 확장자 제외) 형식으로 표기할 것.
- frontmatter에 url이 있으면 불렛에 함께 표기할 것.
