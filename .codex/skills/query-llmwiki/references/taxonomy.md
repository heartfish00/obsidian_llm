# Query LLMWiki taxonomy

## Current vault shape

- Treat the live vault shape as authoritative.
- Many frontmatter keys are stored with trailing colons:
  - `"topics:"`
  - `"index:"`
  - `"mode:"`
  - `"type:"`
  - `"status:"`
  - `"date:"`
  - `"url:"`
  - `"authur:"`
  - `"summary:"`
- `tags` is commonly stored without the trailing colon.
- When reading notes in code, normalize keys in memory by stripping a trailing colon, but do not rewrite notes.

## Closed vocab fields

### mode

- `Meeting`
- `Note`
- `Research`
- `Tutorial`
- `Specification`
- `Report`
- `Analysis`
- `Documentation`

### status

- `inprogress`
- `completed`
- `review`
- `archived`

### type

- `[[PARA_3Resources/2024/tool]]`
- `[[concept]]`
- `[[reference]]`
- `[[guide]]`
- `[[example]]`
- `[[project]]`
- `[[persona_reviewer prd - 페르소나 리뷰어]]`

### topics

- `[[📖 100 연구]]`
- `[[📚 101 RAG 연구]]`
- `[[📚 102 LLM 연구]]`
- `[[📚 103 AI 트렌드]]`
- `[[📚 104 AI 활용 사례]]`
- `[[📚 105 최신 논문]]`
- `[[📖 200 AI & 데이터]]`
- `[[📚 201 Concepts]]`
- `[[📚 202 Prompt]]`
- `[[📚 203 Retriever]]`
- `[[📚 204 Embedding]]`
- `[[📚 205 LLM]]`
- `[[📚 206 LocalModels / Ollama]]`
- `[[📚 207 Vector DB]]`
- `[[📚 208 Reranking]]`
- `[[📚 209 Knowledge Graph]]`
- `[[📚 210 Hybrid Search]]`
- `[[📚 211 Evaluation]]`
- `[[📚 212 HuggingFace]]`
- `[[📚 213 Agent]]`
- `[[📚 214 문서파서]]`
- `[[📚 220 Fine-Tuning]]`
- `[[📚 221 LangChain / LangGraph]]`
- `[[📚 222 vLLM]]`
- `[[📚 230 데이터 분석]]`
- `[[📚 231 머신러닝]]`
- `[[📚 232 딥러닝 (pytorch)]]`
- `[[📚 233 데이터 엔지니어링]]`
- `[[📚 234 이미지 Classification]]`
- `[[📚 235 이미지 Object Dectection]]`
- `[[📚 236 이미지 Segmentation]]`
- `[[📚 250 AI 서비스 구축]]`
- `[[📖 300 개발]]`
- `[[📚 301 Python]]`
- `[[📚 302 Web 개발]]`
- `[[📚 303 AWS & GCP]]`
- `[[📚 304 Docker & Kubernetes]]`
- `[[📚 305 시스템 설계]]`
- `[[📚 306 MLOps & 배포]]`
- `[[📚 307 Git]]`
- `[[📚 308 ngrok]]`
- `[[📚 309 FastAPI]]`
- `[[📚 310 가상환경/패키지관리(PYPI, Poetry, UV)]]`
- `[[📖 400 비즈니스 & 운영]]`
- `[[📚 401 Braincrew 운영]]`
- `[[📚 402 회사]]`
- `[[📚 403 HR]]`
- `[[📚 404 업무용 구매]]`
- `[[📖 500 강의 & 컨설팅]]`
- `[[📚 501 기업 컨설팅]]`
- `[[📚 502 강의 자료]]`
- `[[📚 503 교육 커리큘럼]]`
- `[[📚 504 세미나 & 워크숍]]`
- `[[📖 600 프로젝트]]`
- `[[📚 601 기업 외주 프로젝트]]`
- `[[📚 602 사이드 프로젝트]]`
- `[[📖 700 콘텐츠 & SNS]]`
- `[[📚 701 YouTube]]`
- `[[📚 702 SNS 운영]]`
- `[[📖 800 지식관리 & 생산성]]`
- `[[📚 801 세컨드브레인]]`
- `[[📚 802 메모 & 노트]]`
- `[[📚 803 나의 생각 정리]]`
- `[[📚 804 업무 자동화]]`
- `[[📖 900 Personal & 성장]]`
- `[[📚 901 커리어]]`
- `[[📚 902 네트워킹 & 커뮤니티]]`
- `[[📚 903 개인 구매]]`

### index

- `[[🏷️ 스터디]]`
- `[[🏷️ 강의]]`
- `[[🏷️ 외주 프로젝트]]`
- `[[🏷️ 컨설팅]]`
- `[[🏷️ 사이드 프로젝트]]`
- `[[🏷️ PM]]`
- `[[🏷️ YouTube테디노트]]`
- `[[🏷️ 패스트캠퍼스-주주총회]]`
- `[[🏷️ 커리큘럼]]`
- `[[🏷️ 컨퍼런스]]`
- `[[🏷️ 회사운영]]`
- `[[🏷️ 데일리 노트]]`

## Semi-open fields

### authur

- Use the exact value already present in note frontmatter whenever possible.
- Prefer existing vault values over invented aliases.
- The source templater contains a long allowed list; common high-signal examples include:
  - `[[테디노트 teddynote 이경록]]`
  - `[[조코딩 AI 뉴스]]`
  - `[[생활코딩]]`
  - `[[AWS]]`
  - `[[Gpters]]`
  - `[[개발바닥]]`
  - `[[코딩애플]]`
  - `[[패스트 캠퍼스 패스트캠퍼스 패캠]]`
- If exact author matching is critical, inspect a few matching notes first instead of inventing a new `authur` value.

### tags

- Treat `tags` as explicit surface keywords already present in notes.
- Use them for exact or contains filtering.
- Do not convert tags into embeddings or latent concepts.
- Example values seen in the vault:
  - `RAG`
  - `LLM`
  - `PromptEngineering`
  - `VectorDB`
  - `CoT`
  - `LangChain`

### text_query

- Use `text_query` for plain keyword matching over title, summary, or light metadata text when metadata alone is insufficient.
- Keep it short and literal.
- Do not use `text_query` as a license for vault-wide body scanning at the start.
- Use body text only after title, summary, frontmatter, and direct-link signals have already narrowed the candidate set.

## Source-of-truth rule

- If a closed-vocab value is not listed here, do not invent it.
- If you must mirror the original templater prompt exactly during implementation work, read:
  - `D:\Program Files\Obsidian\docs\query-llmwiki\full_context.md`
