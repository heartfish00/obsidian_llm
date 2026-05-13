from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_query_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        f"# Query Result — {payload['query']}",
        "",
        "## Ranked Notes",
    ]
    if not payload["results"]:
        lines.append("No matching notes found.")
    for idx, row in enumerate(payload["results"], 1):
        lines.extend(
            [
                f"{idx}. {row['title']}",
                f"\t- Path: `{row['path']}`",
                f"\t- Score: `{row['score']}`",
                f"\t- Summary: {row['summary'] or '(none)' }",
            ]
        )
    lines.extend(["", "## Graph", f"- Nodes: {len(payload['graph']['nodes'])}", f"- Edges: {len(payload['graph']['edges'])}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_graph_html(path: Path, graph_payload: dict[str, Any]) -> None:
    data = json.dumps(graph_payload, ensure_ascii=False)
    escaped = data.replace("</", "<\/")
    document = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Graphify Local</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #111827; color: #f9fafb; }}
header {{ padding: 16px 20px; border-bottom: 1px solid #374151; }}
#wrap {{ display: grid; grid-template-columns: 1fr 340px; height: calc(100vh - 70px); }}
svg {{ width: 100%; height: 100%; background: radial-gradient(circle at center, #1f2937, #030712); }}
aside {{ overflow: auto; padding: 16px; border-left: 1px solid #374151; background: #0f172a; }}
.node {{ cursor: pointer; }}
.edge {{ stroke: #6b7280; stroke-opacity: .65; }}
.label {{ fill: #f9fafb; font-size: 12px; pointer-events: none; }}
.card {{ padding: 8px; margin: 6px 0; border: 1px solid #374151; border-radius: 8px; }}
</style>
</head>
<body>
<header><strong>Graphify Local</strong> — metadata/wikilink graph</header>
<div id="wrap"><svg id="graph"></svg><aside><h2>Nodes</h2><div id="nodes"></div></aside></div>
<script id="graph-data" type="application/json">{escaped}</script>
<script>
const payload = JSON.parse(document.getElementById('graph-data').textContent);
const graph = payload.graph || payload;
const nodes = graph.nodes || [];
const edges = graph.edges || [];
const svg = document.getElementById('graph');
const width = svg.clientWidth || 900;
const height = svg.clientHeight || 650;
const cx = width / 2;
const cy = height / 2;
const radius = Math.max(160, Math.min(width, height) * 0.38);
const byId = new Map();
nodes.forEach((n, i) => {{
  const angle = (Math.PI * 2 * i) / Math.max(1, nodes.length);
  n.x = cx + Math.cos(angle) * (n.seed ? radius * 0.45 : radius);
  n.y = cy + Math.sin(angle) * (n.seed ? radius * 0.45 : radius);
  byId.set(n.id, n);
}});
function el(name, attrs) {{
  const e = document.createElementNS('http://www.w3.org/2000/svg', name);
  Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
  svg.appendChild(e);
  return e;
}}
edges.forEach(edge => {{
  const s = byId.get(edge.source); const t = byId.get(edge.target);
  if (!s || !t) return;
  el('line', {{x1:s.x, y1:s.y, x2:t.x, y2:t.y, class:'edge'}});
}});
nodes.forEach(node => {{
  const color = node.seed ? '#f59e0b' : node.kind === 'note' ? '#60a5fa' : '#34d399';
  el('circle', {{cx:node.x, cy:node.y, r:node.seed ? 13 : 9, fill:color, class:'node'}});
  el('text', {{x:node.x + 12, y:node.y + 4, class:'label'}}).textContent = node.label;
}});
document.getElementById('nodes').innerHTML = nodes.map(n => `<div class="card"><strong>${{n.label}}</strong><br><small>${{n.kind}} · ${{n.id}}</small></div>`).join('');
</script>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
