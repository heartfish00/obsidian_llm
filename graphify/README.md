# Graphify Local MVP

로컬 Obsidian Markdown 볼트를 LLM/임베딩 없이 메타데이터와 wikilink 기반 그래프로 색인하고, 검색 중심 부분 그래프와 QA 컨텍스트 파일을 생성하는 MVP임.

## 개념

DB는 전처리된 로컬 인덱스임. 쿼리할 때 매번 Markdown 전체를 읽지 않고, 먼저 Markdown/frontmatter/wikilink를 SQLite + FTS5에 색인한 뒤 쿼리 시 부분 그래프와 컨텍스트 파일을 생성함.

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

## 출력

- `graph.json`: 검색 결과 중심 부분 그래프임
- `graph.html`: 외부 CDN 없이 열 수 있는 정적 HTML 그래프임
- `query-result.md`: 사람/LLM 컨텍스트용 Markdown 결과임
- `query-result.json`: 자동화/MCP 연동용 구조화 결과임

## Git 관리

실제 볼트 기반 DB와 output은 개인 데이터와 대용량 파일이 될 수 있으므로 git에 올리지 않음. `.gitignore`에서 `*.sqlite`, `*.sqlite3`, `graphify/output/`을 제외함.

## 원칙

- LLM 사용 안 함
- 임베딩 사용 안 함
- vector DB 사용 안 함
- semantic inferred edge 생성 안 함
- 모든 edge는 `frontmatter`, `wikilink`, `path` 같은 provenance를 가짐
