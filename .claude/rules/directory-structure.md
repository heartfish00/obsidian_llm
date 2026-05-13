# Vault Directory Structure

```
D:\Sales Planning\obsidian\my\        # 볼트 루트 — 최신 노트는 루트에 직접 생성
│                                       (연도 지나면 PARA_3Resources\YYYY\ 로 이동)
├── *.md                               # 일반 노트 (대부분 루트에 위치)
├── 00. Inbox/                         # 임시 저장
├── PARA_1Projects/                    # PARA - 프로젝트
├── PARA_2Areas/                       # PARA - 영역
├── PARA_3Resources/                   # PARA - 자원 (연도별 아카이브: 2024/, 2025/, ...)
├── PARA_4Achieves/                    # PARA - 아카이브
├── Templetes/                         # Templater 템플릿
├── Templetes_keep(20250619)/          # 템플릿 백업
├── attachments/                       # 첨부파일
├── Chats/                             # 채팅 기록
├── Clippings/                         # 웹 클리핑
├── dataview/                          # Dataview 관련
├── scripts/                           # 자동화 스크립트
├── scripts_codex/                     # Codex 스크립트
├── Spaces/                            # Obsidian Spaces
├── tasks/                             # 작업 관리
├── Settings/                          # 볼트 설정 노트
├── smart-chats/                       # Smart Connections 채팅
├── .obsidian/                         # Obsidian 설정 (숨김)
└── $100/                              # 예산 관련
```

**노트 위치 규칙**: 새 노트는 볼트 루트(`D:\Sales Planning\obsidian\my\`)에 직접 생성. 연도가 지나면 `PARA_3Resources\연도\` 로 이동.

## Topics 카테고리 계층

Templater 메타데이터의 `topics:` 필드에 사용되는 계층 구조:

| 계층 | 아이콘 | 예시 |
|------|--------|------|
| 1st level | 📖 | 📖 100 연구, 📖 200 AI & 데이터 |
| 2nd level | 📚 | 📚 101 RAG 연구, 📚 201 Concepts |
| Index | 🏷️ | 🏷️ 스터디, 🏷️ 강의 |

- 📖 — 1st level (대분류, 100-900 시리즈)
- 📚 — 2nd level (소분류)
- 🏷️ — Index (문서 분류 태그)
