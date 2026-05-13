# Obsidian Wikilink Rules

## Decision Tree — When to Use Which Reference Form

| 상황 | 표기 | 예시 |
|------|------|------|
| **Vault 내부 파일** 일반 참조 (default) | `[[wikilink]]` | `[[📚 101 RAG 연구]]`, `[[🏷️ 스터디]]` |
| **에이전트가 작업 시 자동 로드해야 할** 핵심 파일 | `@` import | `@.claude/rules/frontmatter-standard.md` |
| **Vault 외부 경로** (`D:\DEV\`, `~/.claude/` 등) | 백틱 코드 | `` `D:\DEV\project\index.html` `` |
| 외부 URL · 라이브 사이트 | 그대로 | `https://example.com` |
| 코드 식별자 · 명령어 | 백틱 코드 | `` `pip install` ``, `` `python main.py` `` |

**Default 는 `[[wikilink]]`**. `@` import 와 백틱은 명확한 이유가 있을 때만 사용.

## Rules

1. **Always use wikilinks `[[]]`** for internal references, NOT markdown links
2. **Wikilinks in YAML must be quoted**: `"[[link]]"` not bare `[[link]]`
3. **Emoji prefixes are PART of the filename — never strip them**. `[[📚 101 RAG 연구]]` is correct, `[[101 RAG 연구]]` is wrong (creates orphan file)
4. **Verify before linking**: Before writing a wikilink, confirm the exact filename including emoji prefix
5. **Use aliases for cleaner display**: `[[📚 101 RAG 연구|RAG 연구]]` — the target before `|` must be exact

## Anti-Patterns

```markdown
❌ [[101 RAG 연구]]              # Missing 📚 prefix → orphan file
❌ [[스터디]]                     # Missing 🏷️ prefix → orphan file
❌ @[[CLAUDE.md]]                # @ + wikilink 혼용 — 둘 다 깨짐
❌ 모든 관련 파일을 @ import      # 컨텍스트 낭비
```

```markdown
✅ [[📚 101 RAG 연구]]
✅ [[🏷️ 스터디]]
✅ @.claude/rules/frontmatter-standard.md    # Claude Code context import
✅ `D:\DEV\project\index.html`               # Vault 외부 → 백틱
```
