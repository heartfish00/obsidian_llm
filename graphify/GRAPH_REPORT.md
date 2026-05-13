# GRAPH_REPORT

## MVP 상태

- SEED 계획 작성 완료: `graphify/seed.yaml`
- Python 표준 라이브러리 기반 구현 완료
- SQLite + FTS5 색인 구현 완료
- frontmatter metadata edge 구현 완료
- body wikilink edge 구현 완료
- 1-hop / 2-hop query graph export 구현 완료
- `graph.json`, `graph.html`, `query-result.md`, `query-result.json` 출력 구현 완료
- 실제 볼트 일부 전처리를 위한 `--limit` 및 제외 디렉터리 옵션 구현 완료

## DB 전처리 의미

DB는 Markdown 전체를 매번 읽지 않기 위한 로컬 전처리 인덱스임. `build` 단계에서 노트, 메타데이터 노드, wikilink edge, FTS 검색 레코드를 저장하고, `query` 단계에서 DB를 기준으로 결과와 부분 그래프를 생성함.

## 검증 명령

```bash
python3 -m py_compile graphify/graphify_local/*.py
python3 -m unittest discover -s graphify/tests -v
PYTHONPATH=graphify python3 -m graphify_local.cli build --vault "/mnt/d/Sales Planning/obsidian/my" --db graphify/output/real-subset/vault_graph.sqlite --limit 50
PYTHONPATH=graphify python3 -m graphify_local.cli query --db graphify/output/real-subset/vault_graph.sqlite --query "RAG" --hops 2 --out-dir graphify/output/real-subset
```

## Git 제외

실제 볼트 기반 DB와 output은 개인 데이터와 대용량 파일 가능성이 있으므로 commit하지 않음. `.gitignore`에서 `*.sqlite`, `*.sqlite3`, `graphify/output/`을 제외함.

## 제한

- YAML 파서는 MVP용 단순 parser임
- Obsidian plugin은 구현하지 않음
- semantic inferred edge는 생성하지 않음

## 실제 볼트 일부 검증 결과

- 실행 범위: `/mnt/d/Sales Planning/obsidian/my` 중 최대 50개 Markdown
- 전처리 결과: notes 50, nodes 425, edges 591
- 쿼리: `RAG`, `--hops 2`
- 출력 검증: `query-result.json`, `graph.json`, `graph.html` embedded JSON parse 성공
- 출력 위치: `graphify/output/real-subset/`이며 git에는 포함하지 않음
