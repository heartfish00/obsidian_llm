# CLAUDE.md

이 파일은 Claude Code가 이 Obsidian 볼트에서 작업할 때 따라야 할 규칙을 정의한다.

## 볼트 정보

- **OS**: Windows 11
- **볼트 경로**: `D:\Sales Planning\obsidian\my\`
- **구조**: PARA (Projects, Areas, Resources, Archives)
- **메타데이터**: Templater + Gemini API 자동 생성

## Pre-Flight Checklist (Before Every Write/Edit)

- [ ] **YAML frontmatter uses 2 SPACES** (not tabs)
- [ ] **Markdown body uses TAB** (not spaces)
- [ ] **No unnecessary blank lines** between heading→sub-heading, heading→content, list end→next heading (Obsidian-tight)
- [ ] **Trailing colon 키는 따옴표로 감싸기**: `"mode:":` not `mode:`
- [ ] **Wikilinks in YAML are quoted**: `"[[link]]"` not `[[link]]`
- [ ] **Mermaid labels are quoted**: `A["label"]`, no `[/` start
- [ ] **Frontmatter follows Templater schema**: mode:, tags, type:, topics:, status:, date:, summary:

## Templater Metadata Schema (Quick Reference)

@.claude/rules/frontmatter-standard.md

필수 7개: `"mode:"`, `tags`, `"type:"`, `"topics:"`, `"status:"`, `"date:"`, `"summary:"`
선택 3개: `"url:"`, `"index:"`, `"AUTHOR:"`

## Formatting Rules

@.claude/rules/indentation-rules.md
@.claude/rules/blank-line-rules.md
@.claude/rules/wikilink-rules.md
@.claude/rules/mermaid-rules.md

## File Creation

@.claude/rules/file-creation-rules.md

## Directory Structure

@.claude/rules/directory-structure.md

## Essential (Post-Compact)

1. **YAML: 2 SPACES** / **Markdown body: TAB**
2. **Trailing colon 키 따옴표**: `"mode:":`, `"type:":`, `"topics:":` 등. 단 `tags:`는 예외
3. **Wikilinks in YAML: `"[[link]]"`**
4. **빈 줄 최소화 (Obsidian-tight)**
5. **Templater 스키마 준수**: mode(Mode값), tags(평문), type(wikilink), topics(wikilink), status(4값), date(오늘포함), summary(불렛)
6. **이모지 prefix 정확히**: `[[📚 101 RAG 연구]]` not `[[101 RAG 연구]]`
7. **Mermaid 라벨 따옴표**: `A["label"]`
8. **파일 위치**: `00. Inbox/` 하위, 파일명 `YYYY-MM-DD-description.ext`
