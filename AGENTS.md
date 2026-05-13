# AGENTS.md

이 파일은 Claude Code 외의 AI 코딩 에이전트(Codex, Cursor, Windsurf 등)가 이 Obsidian 볼트에서 작업할 때 따라야 할 규칙을 정의한다.

## 볼트 정보

- **OS**: Windows 11
- **볼트 경로**: `D:\Sales Planning\obsidian\my\`
- **노트 위치**: 새 노트는 볼트 루트에 직접 생성 (연도 지나면 `PARA_3Resources\연도\` 로 이동)
- **메타데이터**: Templater + Gemini API 자동 생성

## Pre-Flight Checklist (Before Every Write/Edit)

- [ ] **YAML frontmatter uses 2 SPACES** (not tabs)
- [ ] **Markdown body uses TAB** (not spaces)
- [ ] **No unnecessary blank lines** (Obsidian-tight)
- [ ] **Trailing colon 키는 따옴표**: `"mode:":` not `mode:`
- [ ] **Wikilinks in YAML are quoted**: `"[[link]]"` not `[[link]]`
- [ ] **Mermaid labels are quoted**: `A["label"]`
- [ ] **Frontmatter follows Templater schema**

## Templater Metadata Schema

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
8. **새 노트는 볼트 루트에 생성**: `D:\Sales Planning\obsidian\my\YYYY-MM-DD-description.md`
9. **코드 산출물**: `00. Inbox/` 하위

## Rule Loading

`@path/to/file.md` 는 Claude Code import 규약. 다른 에이전트는 아래 파일들을 직접 읽어야 함:

- `.claude/rules/frontmatter-standard.md`
- `.claude/rules/indentation-rules.md`
- `.claude/rules/wikilink-rules.md`
- `.claude/rules/blank-line-rules.md`
- `.claude/rules/file-creation-rules.md`
- `.claude/rules/directory-structure.md`

## Codex Output Path

Codex 코드 산출물은 `00. Inbox/` 하위에 저장. 다중 파일은 `YYYY-MM-DD-project-name/` 폴더 생성.

## Codex Command Mapping

| Claude 명령 | Codex 대체 |
|------------|-----------|
| Read/Glob/Grep | `rg`, `find`, `cat` |
| Write/Edit | `apply_patch` 또는 파일 직접 쓰기 |
| AskUserQuestion | 간결한 텍스트 질문 |

## Wikilinks

```markdown
[[Note Name]]              # 기본 링크
[[Note Name|Display Text]] # 별칭 링크
[[Note Name#Heading]]      # 헤딩 링크
![[Note Name]]             # 파일 임베드
```
