# Graphify Local MVP

로컬 Obsidian Markdown 볼트를 메타데이터와 wikilink 기반 그래프로 색인하고, 검색 중심 부분 그래프와 QA 컨텍스트 파일을 생성하는 MVP임. 기본 검색은 로컬 SQLite/FTS5만 사용하며, 옵션으로 xAI Responses API의 `x_search`를 호출해 X/Twitter 실시간 맥락을 그래프에 덧붙일 수 있음.

## 개념

DB는 전처리된 로컬 인덱스임. 쿼리할 때 매번 Markdown 전체를 읽지 않고, 먼저 Markdown/frontmatter/wikilink를 SQLite + FTS5에 색인한 뒤 쿼리 시 부분 그래프와 컨텍스트 파일을 생성함. `--search-x`를 지정하면 같은 쿼리를 xAI `x_search` 도구에도 보내고, 응답 요약/citation URL을 `x_search`, `x_post` 외부 노드와 `xai.responses.x_search` provenance edge로 추가함.

## NetworkX 그래프 메트릭

빌드 단계에서 `nodes`/`edges`를 기반으로 `node_metrics`와 `graph_meta`를 함께 생성함. `networkx`가 설치되어 있으면 NetworkX PageRank/degree centrality/connected component 계산을 사용하고, 설치되어 있지 않으면 로컬 fallback으로 degree와 component 정보를 계산함. 따라서 기본 MVP는 추가 의존성 없이 동작하지만, 더 정교한 그래프 메트릭이 필요하면 실행 환경에 `networkx`를 설치하면 됨.

쿼리 결과의 `graph.nodes[].metrics`에는 `degree`, `in_degree`, `out_degree`, `degree_centrality`, `pagerank`, `component_id`, `component_size`, `backend`가 포함됨. `query-result.md`와 `graph.html`에도 주요 메트릭이 노출됨.

## 빠른 검증

```bash
PYTHONPATH=graphify python3 -m graphify_local.cli build \
  --vault graphify/tests/fixtures/vault \
  --db graphify/demo/vault_graph.sqlite

PYTHONPATH=graphify python3 -m graphify_local.cli query \
  --db graphify/demo/vault_graph.sqlite \
  --query "RAG 평가" \
  --hops 2 \
  --out-dir graphify/demo
```

## 실제 볼트 일부 전처리

```bash
PYTHONPATH=graphify python3 -m graphify_local.cli build \
  --vault "/mnt/d/Sales Planning/obsidian/my" \
  --db graphify/output/real-subset/vault_graph.sqlite \
  --limit 50

PYTHONPATH=graphify python3 -m graphify_local.cli query \
  --db graphify/output/real-subset/vault_graph.sqlite \
  --query "RAG" \
  --hops 2 \
  --out-dir graphify/output/real-subset
```

기본 제외 디렉터리는 `.git`, `.obsidian`, `.omx`, `.trash`, `.pytest_cache`, `graphify`임. 추가 제외가 필요하면 `--exclude-dir 이름`을 반복해서 지정함.

## Search X 연동

Search X는 네트워크/API 키가 필요한 선택 기능임. 의존성 추가 없이 Python 표준 라이브러리로 `POST https://api.x.ai/v1/responses`를 호출함. `XAI_API_KEY`는 shell 환경변수 또는 repo root `.env`에서 자동 로드하며, `.env`는 gitignore 대상임.

```bash
export XAI_API_KEY="xai-..."
# 또는 repo root .env:
# XAI_API_KEY=xai-...

PYTHONPATH=graphify python3 -m graphify_local.cli query \
  --db graphify/output/full/vault_graph.sqlite \
  --query "AI agent graph search" \
  --hops 2 \
  --search-x \
  --x-from-date 2026-05-01 \
  --x-to-date 2026-05-13 \
  --out-dir graphify/output/ai-agent-graph-search
```

지원 옵션:

- `--search-x`: xAI Responses API `x_search` 호출을 켬
- `--x-model`: 기본값은 `SEARCH_X_MODEL` 또는 `grok-4.3`
- `--x-allowed-handles`: 특정 X 핸들만 포함함, 쉼표 구분, 최대 10개
- `--x-excluded-handles`: 특정 X 핸들을 제외함, 쉼표 구분, 최대 10개
- `--x-from-date`, `--x-to-date`: `YYYY-MM-DD` 기간 필터
- `--x-timeout`: HTTP timeout 초

`XAI_API_KEY`가 없으면 실패하지 않고 `query-result.json` / `query-result.md`에 `missing_api_key` 상태를 기록함.

## 출력

- `graph.json`: 검색 결과 중심 부분 그래프임
- `graph.html`: 외부 CDN 없이 열 수 있는 정적 HTML 그래프임
- `query-result.md`: 사람/LLM 컨텍스트용 Markdown 결과임
- `query-result.json`: 자동화/MCP 연동용 구조화 결과임
- `graph.nodes[].metrics`: NetworkX 또는 fallback 기반 노드 메트릭임

## Git 관리

실제 볼트 기반 DB와 output은 개인 데이터와 대용량 파일이 될 수 있으므로 git에 올리지 않음. `.gitignore`에서 `*.sqlite`, `*.sqlite3`, `graphify/output/`을 제외함.

## 원칙

- 기본 로컬 검색은 LLM 사용 안 함
- 기본 로컬 검색은 임베딩 사용 안 함
- vector DB 사용 안 함
- semantic inferred edge 생성 안 함
- 모든 edge는 `frontmatter`, `wikilink`, `path` 같은 provenance를 가짐
- Search X 외부 보강 edge는 `xai.responses.x_search` provenance를 명시함
