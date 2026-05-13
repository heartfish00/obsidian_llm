from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"
DEFAULT_X_MODEL = "grok-4.3"


def dotenv_paths() -> list[Path]:
    paths = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def load_dotenv_if_present() -> None:
    for path in dotenv_paths():
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def split_handles(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().lstrip("@") for part in value.split(",") if part.strip()]


def extract_response_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()

    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content") or []
        if isinstance(content, str):
            chunks.append(content)
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text") or block.get("content")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip())


def extract_citations(data: dict[str, Any]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: Any, title: Any = None) -> None:
        if not isinstance(url, str) or not url:
            return
        if url in seen:
            return
        seen.add(url)
        citations.append({"url": url, "title": str(title or url)})

    for citation in data.get("citations") or []:
        if isinstance(citation, str):
            add(citation)
        elif isinstance(citation, dict):
            add(citation.get("url"), citation.get("title") or citation.get("text"))

    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            for annotation in block.get("annotations") or []:
                if not isinstance(annotation, dict):
                    continue
                add(annotation.get("url"), annotation.get("title") or annotation.get("text"))
    return citations


def search_x_posts(
    query: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    allowed_handles: list[str] | None = None,
    excluded_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    load_dotenv_if_present()
    api_key = api_key if api_key is not None else os.getenv("XAI_API_KEY", "")
    model = model or os.getenv("SEARCH_X_MODEL") or DEFAULT_X_MODEL
    if not api_key:
        return {
            "enabled": True,
            "status": "missing_api_key",
            "provider": "xai.responses.x_search",
            "model": model,
            "summary": "",
            "citations": [],
            "error": "Set XAI_API_KEY to enable Graphify Search X augmentation.",
        }

    allowed_handles = allowed_handles or []
    excluded_handles = excluded_handles or []
    if allowed_handles and excluded_handles:
        return {
            "enabled": True,
            "status": "invalid_config",
            "provider": "xai.responses.x_search",
            "model": model,
            "summary": "",
            "citations": [],
            "error": "allowed_x_handles and excluded_x_handles cannot be used together.",
        }

    tool: dict[str, Any] = {"type": "x_search"}
    if allowed_handles:
        tool["allowed_x_handles"] = allowed_handles[:10]
    if excluded_handles:
        tool["excluded_x_handles"] = excluded_handles[:10]
    if from_date:
        tool["from_date"] = from_date
    if to_date:
        tool["to_date"] = to_date

    payload = {
        "model": model,
        "input": [{"role": "user", "content": query}],
        "tools": [tool],
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        XAI_RESPONSES_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        return {
            "enabled": True,
            "status": "http_error",
            "provider": "xai.responses.x_search",
            "model": model,
            "summary": "",
            "citations": [],
            "error": f"HTTP {exc.code}: {detail}",
        }
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "enabled": True,
            "status": "error",
            "provider": "xai.responses.x_search",
            "model": model,
            "summary": "",
            "citations": [],
            "error": str(exc),
        }

    return {
        "enabled": True,
        "status": "ok",
        "provider": "xai.responses.x_search",
        "model": model,
        "response_id": data.get("id"),
        "summary": extract_response_text(data),
        "citations": extract_citations(data),
    }


def attach_x_search_context(payload: dict[str, Any], x_search: dict[str, Any]) -> dict[str, Any]:
    augmented = deepcopy(payload)
    augmented["x_search"] = x_search

    graph = augmented.setdefault("graph", {})
    nodes = graph.setdefault("nodes", [])
    edges = graph.setdefault("edges", [])
    existing_node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    existing_edges = {
        (edge.get("source"), edge.get("target"), edge.get("relation"), edge.get("provenance"))
        for edge in edges
        if isinstance(edge, dict)
    }

    query_node_id = f"x_search:{payload.get('query', '')}"
    if query_node_id not in existing_node_ids:
        nodes.append({"id": query_node_id, "kind": "x_search", "label": "Search X", "seed": False})
        existing_node_ids.add(query_node_id)

    for note_id in graph.get("seed_note_ids") or []:
        edge_key = (note_id, query_node_id, "augmented_by", "xai.responses.x_search")
        if edge_key not in existing_edges:
            edges.append(
                {
                    "source": note_id,
                    "target": query_node_id,
                    "relation": "augmented_by",
                    "provenance": "xai.responses.x_search",
                    "confidence": 1.0,
                }
            )
            existing_edges.add(edge_key)

    for idx, citation in enumerate(x_search.get("citations") or [], 1):
        url = citation.get("url")
        if not url:
            continue
        node_id = f"x_post:{url}"
        if node_id not in existing_node_ids:
            nodes.append(
                {
                    "id": node_id,
                    "kind": "x_post",
                    "label": citation.get("title") or f"X citation {idx}",
                    "url": url,
                    "seed": False,
                }
            )
            existing_node_ids.add(node_id)
        edge_key = (query_node_id, node_id, "x_search_result", "xai.responses.x_search")
        if edge_key not in existing_edges:
            edges.append(
                {
                    "source": query_node_id,
                    "target": node_id,
                    "relation": "x_search_result",
                    "provenance": "xai.responses.x_search",
                    "confidence": 1.0,
                }
            )
            existing_edges.add(edge_key)
    return augmented
