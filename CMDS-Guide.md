# CMDS Guide

Properties 표준 및 운영 가이드. Templater + Gemini API 기반 메타데이터 스키마를 따른다.

## Properties

### 필수 Properties (7개)

```yaml
---
"mode:": Note
tags:
  - 태그1
"type:":
  - "[[concept]]"
"topics:":
  - "[[📚 201 Concepts]]"
"status:": inprogress
"date:":
  - "[[2026-05-13]]"
"summary:": |-
  - 🔹 첫번째 요약문장임
  - 🔸 두번째 요약문장임
---
```

### 선택 Properties (3개)

```yaml
"url:":
  - https://example.com
"index:":
  - "[[🏷️ 스터디]]"
"AUTHOR:":
  - "[[테디노트 teddynote 이경록]]"
```

### 키 명명 규칙

| 패턴 | 사용 시점 | 예시 |
|------|----------|------|
| **trailing colon + 따옴표** | `tags` 제외 모든 프로퍼티 | `"mode:":`, `"type:":`, `"topics:":` |
| **소문자** | `tags`만 | `tags:` |
| **대문자 + colon** | AUTHOR만 | `"AUTHOR:":` |

YAML에서 colon이 포함된 키는 반드시 따옴표로 감싸야 파서가 정상 동작한다.

### mode: 값

| 값 | 용도 |
|----|------|
| Meeting | 회의록, 미팅 |
| Note | 일반 노트 |
| Research | 연구, 조사 |
| Tutorial | 학습 가이드 |
| Specification | 사양서, 명세서 |
| Report | 보고서 |
| Analysis | 분석 |
| Documentation | 기술 문서 |

### type: 값 (wikilink 배열)

| 값 | 용도 |
|----|------|
| `[[PARA_3Resources/2024/tool]]` | 도구/기술 |
| `[[concept]]` | 개념/이론 |
| `[[reference]]` | 참고자료 |
| `[[guide]]` | 가이드/지침 |
| `[[example]]` | 예제/샘플 |
| `[[project]]` | 프로젝트 |
| `[[persona_reviewer prd - 페르소나 리뷰어]]` | 개인적 내용 |

### status: 값

| 값 | 의미 |
|----|------|
| inprogress | 작성 중 |
| completed | 완료됨 |
| review | 검토 필요 |
| archived | 보관됨 |

### topics: 카테고리 (wikilink 배열, 1-3개 선택)

- 📖 100 연구: 📚 101 RAG 연구 · 📚 102 LLM 연구 · 📚 103 AI 트렌드 · 📚 104 AI 활용 사례 · 📚 105 최신 논문
- 📖 200 AI & 데이터: 📚 201~250 (Concepts, Prompt, Retriever, Embedding, LLM, Ollama, Vector DB, Reranking, Knowledge Graph, Hybrid Search, Evaluation, HuggingFace, Agent, 문서파서, Fine-Tuning, LangChain/LangGraph, vLLM, 데이터분석, 머신러닝, 딥러닝, 데이터엔지니어링, 이미지Classification/Detection/Segmentation, AI서비스구축)
- 📖 300 개발: 📚 301~310 (Python, Web, AWS&GCP, Docker&K8s, 시스템설계, MLOps, Git, ngrok, FastAPI, 가상환경)
- 📖 400 비즈니스 & 운영: 📚 401 Braincrew · 📚 402 회사 · 📚 403 HR · 📚 404 업무용구매
- 📖 500 강의 & 컨설팅: 📚 501 기업컨설팅 · 📚 502 강의자료 · 📚 503 커리큘럼 · 📚 504 세미나&워크숍
- 📖 600 프로젝트: 📚 601 기업외주 · 📚 602 사이드프로젝트
- 📖 700 콘텐츠 & SNS: 📚 701 YouTube · 📚 702 SNS운영
- 📖 800 지식관리 & 생산성: 📚 801 세컨드브레인 · 📚 802 메모&노트 · 📚 803 나의생각정리 · 📚 804 업무자동화
- 📖 900 Personal & 성장: 📚 901 커리어 · 📚 902 네트워킹 · 📚 903 개인구매

### index: 분류 (wikilink 배열, 1-2개 선택)

🏷️ 스터디 · 🏷️ 강의 · 🏷️ 외주 프로젝트 · 🏷️ 컨설팅 · 🏷️ 사이드 프로젝트 · 🏷️ PM · 🏷️ YouTube테디노트 · 🏷️ 패스트캠퍼스-주주총회 · 🏷️ 커리큘럼 · 🏷️ 컨퍼런스 · 🏷️ 회사운영 · 🏷️ 데일리 노트

### date: 규칙

- 본문에 언급된 날짜(`YYYY-MM-DD`)를 모두 추출
- **항상 오늘 날짜 포함**
- 중복 제거 후 정렬
- 형식: `[[YYYY-MM-DD]]` wikilink

### summary: 규칙

- 불렛포인트 3-5줄
- 각 줄 앞에 이모지 1개 (`- 🔹`, `- 🔸` 등)
- 어미: ~임, ~함 (간결)
- 핵심 개념과 구체적 수치만 포함

## Folder Structure

```
D:\Sales Planning\obsidian\my\        # 볼트 루트 — 최신 노트는 루트에 직접 생성
│                                       (연도 지나면 PARA_3Resources\YYYY\ 로 이동)
├── *.md                               # 일반 노트 (대부분 루트에 위치)
├── 00. Inbox/                         # 임시 저장
├── PARA_1Projects/                    # 프로젝트
├── PARA_2Areas/                       # 영역
├── PARA_3Resources/                   # 자원 (연도별 아카이브: 2024/, 2025/, ...)
├── PARA_4Achieves/                    # 아카이브
├── Templetes/                         # Templater 템플릿
├── attachments/                       # 첨부파일
├── Chats/                             # 채팅 기록
├── Clippings/                         # 웹 클리핑
├── scripts/                           # 자동화 스크립트
├── tasks/                             # 작업 관리
└── Settings/                          # 볼트 설정
```

**노트 위치**: 새 노트는 루트에 생성. 연도가 지나면 `PARA_3Resources\연도\` 로 이동.

## Template Examples

### 기본 노트

```yaml
---
"mode:": Note
tags:
  -
"type:":
  - "[[concept]]"
"topics:":
  - "[[📚 201 Concepts]]"
"status:": inprogress
"date:":
  - "[[2026-05-13]]"
"summary:": |-
  -
---
```

### 연구 노트

```yaml
---
"mode:": Research
tags:
  - RAG
  - vectorDB
"type:":
  - "[[reference]]"
"topics:":
  - "[[📚 101 RAG 연구]]"
  - "[[📚 207 Vector DB]]"
"status:": inprogress
"date:":
  - "[[2026-05-13]]"
"summary:": |-
  - 🔹 요약1
  - 🔸 요약2
"url:":
  - https://example.com/paper
"index:":
  - "[[🏷️ 스터디]]"
"AUTHOR:":
  -
---
```

### 회의록

```yaml
---
"mode:": Meeting
tags:
  - 회의
"type:":
  - "[[project]]"
"topics:":
  - "[[📚 601 기업 외주 프로젝트]]"
"status:": completed
"date:":
  - "[[2026-05-13]]"
"summary:": |-
  - 🔹 회의 요약1
  - 🔸 회의 요약2
"index:":
  - "[[🏷️ 컨설팅]]"
---
```
