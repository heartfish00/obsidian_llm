# Prompt examples

## Example 1

### User query

`최근 테디노트가 유튜브에서 말한 RAG 관련 내용 요약해줘`

### Expected routing shape

```json
{
  "topics_filter": ["[[📚 101 RAG 연구]]"],
  "index_filter": ["[[🏷️ YouTube테디노트]]"],
  "authur_filter": ["[[테디노트 teddynote 이경록]]"],
  "tags_filter": ["RAG"],
  "text_query": "요약"
}
```

## Example 2

### User query

`LangChain이나 LangGraph 관련 실무 메모 찾아줘`

### Expected routing shape

```json
{
  "topics_filter": ["[[📚 221 LangChain / LangGraph]]"],
  "index_filter": [],
  "authur_filter": [],
  "tags_filter": ["LangChain", "LangGraph"],
  "text_query": "실무"
}
```

## Example 3

### User query

`파이썬으로 RAG 구현 관련해서 최근에 정리한 내용만 모아줘`

### Expected routing shape

```json
{
  "topics_filter": ["[[📚 101 RAG 연구]]", "[[📚 301 Python]]"],
  "index_filter": [],
  "authur_filter": [],
  "tags_filter": ["RAG", "Python"],
  "text_query": "최근"
}
```

## Example 4

### User query

`AI 에이전트와 온톨로지 관련 비교 메모 찾아줘`

### Expected routing shape

```json
{
  "topics_filter": ["[[📚 213 Agent]]"],
  "index_filter": ["[[🏷️ 스터디]]"],
  "authur_filter": [],
  "tags_filter": ["Ontology", "AI_Agent"],
  "text_query": "비교"
}
```

## Example 5

### User query

`요즘 broad하게 AI 트렌드 정리해줘`

### Expected behavior

- Route to a broad metadata slice such as `[[📚 103 AI 트렌드]]`.
- Expect many hits.
- Keep the search root vault-wide, but start with the default low-noise pass instead of scanning every folder equally.
- Switch to title + summary + url context packing before final answer generation.

## Example 6

### User query

`임팩티어 관련 노트 찾아서 뭘 했는지 알려줘`

### Expected behavior

- Keep the search root vault-wide. Do not hard-scope to `PARA_3Resources`.
- Try a small number of literal variants first, such as `임팩티어`, `임펙티어`, and `impactier`.
- Start with title, filename, wiki-link, and frontmatter matches before any body search.
- Skip default clutter folders on the first pass, but re-include them if the first pass is empty or if the answer still lacks evidence.
- Read only frontmatter plus the first 20 lines for most candidates, then open the full body for only the final evidence-carrying notes.
