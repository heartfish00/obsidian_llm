# Frontmatter Standard (Templater Metadata Schema)

모든 노트의 frontmatter는 Templater + Gemini API 기반 메타데이터 스키마를 따른다.

## 필수 프로퍼티 (7개)

```yaml
---
"mode:": Note
tags:
  - 태그1
  - 태그2
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

## 선택 프로퍼티 (3개)

```yaml
"url:":
  - https://example.com
"index:":
  - "[[🏷️ 스터디]]"
"AUTHOR:":
  - "[[테디노트 teddynote 이경록]]"
```

## 키 명명 규칙

**YAML에서 trailing colon 키는 반드시 따옴표로 감싼다.** `tags`만 예외.

| 키 | YAML 표기 | 따옴표 |
|----|----------|--------|
| mode | `"mode:":` | 필수 |
| tags | `tags:` | 불필요 |
| type | `"type:":` | 필수 |
| topics | `"topics:":` | 필수 |
| status | `"status:":` | 필수 |
| date | `"date:":` | 필수 |
| summary | `"summary:":` | 필수 |
| url | `"url:":` | 필수 |
| index | `"index:":` | 필수 |
| AUTHOR | `"AUTHOR:":` | 필수 |

## 값 규칙

### mode: (문서 형식, 단일값)

Meeting | Note | Research | Tutorial | Specification | Report | Analysis | Documentation

### tags (배열, 평문)

- `#` 기호 없이 평문으로 작성
- 기술 용어는 영어 유지 (RAG, LLM 등)
- 한국어와 영어 혼용 가능

### type: (문서 종류, wikilink 배열)

- `[[PARA_3Resources/2024/tool]]` — 도구/기술
- `[[concept]]` — 개념/이론
- `[[reference]]` — 참고자료
- `[[guide]]` — 가이드/지침
- `[[example]]` — 예제/샘플
- `[[project]]` — 프로젝트
- `[[persona_reviewer prd - 페르소나 리뷰어]]` — 개인적 내용

### topics: (주제 카테고리, wikilink 배열, 1-3개)

#### 📖 100 연구
- [[📚 101 RAG 연구]], [[📚 102 LLM 연구]], [[📚 103 AI 트렌드]], [[📚 104 AI 활용 사례]], [[📚 105 최신 논문]]

#### 📖 200 AI & 데이터
- [[📚 201 Concepts]], [[📚 202 Prompt]], [[📚 203 Retriever]], [[📚 204 Embedding]], [[📚 205 LLM]], [[📚 206 LocalModels / Ollama]], [[📚 207 Vector DB]], [[📚 208 Reranking]], [[📚 209 Knowledge Graph]], [[📚 210 Hybrid Search]], [[📚 211 Evaluation]], [[📚 212 HuggingFace]], [[📚 213 Agent]], [[📚 214 문서파서]], [[📚 220 Fine-Tuning]], [[📚 221 LangChain / LangGraph]], [[📚 222 vLLM]], [[📚 230 데이터 분석]], [[📚 231 머신러닝]], [[📚 232 딥러닝 (pytorch)]], [[📚 233 데이터 엔지니어링]], [[📚 234 이미지 Classification]], [[📚 235 이미지 Object Dectection]], [[📚 236 이미지 Segmentation]], [[📚 250 AI 서비스 구축]]

#### 📖 300 개발
- [[📚 301 Python]], [[📚 302 Web 개발]], [[📚 303 AWS & GCP]], [[📚 304 Docker & Kubernetes]], [[📚 305 시스템 설계]], [[📚 306 MLOps & 배포]], [[📚 307 Git]], [[📚 308 ngrok]], [[📚 309 FastAPI]], [[📚 310 가상환경/패키지관리(PYPI, Poetry, UV)]]

#### 📖 400 비즈니스 & 운영
- [[📚 401 Braincrew 운영]], [[📚 402 회사]], [[📚 403 HR]], [[📚 404 업무용 구매]]

#### 📖 500 강의 & 컨설팅
- [[📚 501 기업 컨설팅]], [[📚 502 강의 자료]], [[📚 503 교육 커리큘럼]], [[📚 504 세미나 & 워크숍]]

#### 📖 600 프로젝트
- [[📚 601 기업 외주 프로젝트]], [[📚 602 사이드 프로젝트]]

#### 📖 700 콘텐츠 & SNS
- [[📚 701 YouTube]], [[📚 702 SNS 운영]]

#### 📖 800 지식관리 & 생산성
- [[📚 801 세컨드브레인]], [[📚 802 메모 & 노트]], [[📚 803 나의 생각 정리]], [[📚 804 업무 자동화]]

#### 📖 900 Personal & 성장
- [[📚 901 커리어]], [[📚 902 네트워킹 & 커뮤니티]], [[📚 903 개인 구매]]

### status: (문서 상태, 단일값)

inprogress | completed | review | archived

### date: (날짜, wikilink 배열)

- 본문에 언급된 날짜 + **항상 오늘 날짜 포함**
- 형식: `[[YYYY-MM-DD]]`
- 중복 제거 후 정렬

### summary: (요약, 멀티라인 문자열)

- 불렛포인트 3-5줄
- 각 줄 앞에 이모지 1개
- 어미: ~임, ~함 (간결)
- 핵심 개념과 수치만 포함

### index: (문서 분류, wikilink 배열, 1-2개)

- [[🏷️ 스터디]], [[🏷️ 강의]], [[🏷️ 외주 프로젝트]], [[🏷️ 컨설팅]], [[🏷️ 사이드 프로젝트]], [[🏷️ PM]], [[🏷️ YouTube테디노트]], [[🏷️ 패스트캠퍼스-주주총회]], [[🏷️ 커리큘럼]], [[🏷️ 컨퍼런스]], [[🏷️ 회사운영]], [[🏷️ 데일리 노트]]

### AUTHOR: (작성자, wikilink 배열)

- 템플릿에 등록된 인물 목록에서 선택 또는 새로 추가
- 항상 `[[]]` wikilink 형식

### url: (출처 URL, 배열)

- 본문에서 참조한 주요 URL
