---
name: care-orphan-llmwiki
description: Find and repair Obsidian orphan notes without any LLM or API calls. Use when Codex needs to scan a Markdown vault, detect weak or missing `author` metadata plus missing backlinks among notes that share title-backed core keywords or authors, and apply minimal safe fixes with `ruamel.yaml` frontmatter preservation and append-only `[[...]]` backlink blocks.
---

# Care Orphan LLMWiki

Use this skill to repair orphan notes in an Obsidian vault with deterministic local code only.

## Workflow

1. Run `scripts/link_orphans.py --vault <vault-path>` in the default `interactive` mode to preview candidates and approve changes note by note.
2. Use `--mode preview` for a read-only report or `--mode apply --yes` for unattended batch application.
3. The script **hardcodes** its processing scope to root-level `.md` files and `PARA_*` subdirectories only (auto-detected). Non-PARA folders (`Chats/`, `Clippings/`, `00. Inbox/`, etc.) are always skipped. The file `그루,구루 대분류 AI.md` is also excluded. Safe to run on the full vault without `--path-glob`.
4. Use `--limit`, `--path-glob`, `--target-path-glob`, or `--exclude-dir` to further narrow scope on top of the hardcoded baseline.
5. Preserve existing YAML structure with `ruamel.yaml`; normalize legacy `authur` input into `author`, keep `core_shared_keywords` in sync, and only derive fallback `author` values from a deterministic domain.
6. Never insert backlinks into the middle of the body. Only append a bottom block in this format:

```markdown
---
🔗 **Shared Keywords:** [[note-a]], [[note-b]]

---
🔗 **Shared Authors:** [[note-c]]
```

## What the script does

- Build a local reverse index from `keywords` and `tags`, but only treat values that also appear in the note title as `core_shared_keywords`.
- When a note has no `keywords` or `tags` in frontmatter, automatically derive keywords from title tokens so the note can still be matched.
- Flag notes whose `author` is missing, blank, or 2 characters or fewer, while accepting legacy `authur` as read-only input.
- Derive fallback author values from the `url`, `source`, or `source_url` domain when possible.
- With `--author-ref`, match authors from a reference note's AUTHOR field via body wikilinks and title token overlap (takes priority over domain fallback).
- Find notes that share one or more `core_shared_keywords` or the same `author/authur` value and are not already linked in the body.
- Write `core_shared_keywords` back into frontmatter and normalize output to the `author` field.
- Skip malformed YAML with logged errors instead of aborting the run.
- Keep modifications minimal: frontmatter `core_shared_keywords` / `author`, plus append-only backlink blocks.

## Key commands

```bash
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my"
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my" --mode preview --limit 20
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my" --mode apply --yes
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my" --path-glob "PARA_3Resources/**/*.md"
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my" --mode preview --target-path-glob "PARA_1Projects/*" --preview-link-limit 10
python scripts/link_orphans.py --vault "D:\Sales Planning\obsidian\my" --mode preview --target-path-glob "PARA_1Projects/*" --author-ref "PARA_3Resources/2024/그루,구루 대분류 AI.md"
```

## Resources

- `scripts/link_orphans.py`: Zero-LLM orphan detection and repair CLI.
- `references/algorithm.md`: Detection rules, safety constraints, and phase notes.

## Phase scaffold

This workspace also contains `tasks/care-orphan-llmwiki/`, prepared in the `scripts_codex/run-phases.py` format. Use it when the user wants the skill iterated via explicit phase prompts instead of direct manual execution.
