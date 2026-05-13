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
    x_search = payload.get("x_search")
    if x_search:
        lines.extend(
            [
                "",
                "## Search X",
                f"- Status: `{x_search.get('status', 'unknown')}`",
                f"- Provider: `{x_search.get('provider', 'xai.responses.x_search')}`",
                f"- Model: `{x_search.get('model', '')}`",
            ]
        )
        if x_search.get("error"):
            lines.append(f"- Error: {x_search['error']}")
        if x_search.get("summary"):
            lines.extend(["", x_search["summary"]])
        citations = x_search.get("citations") or []
        if citations:
            lines.extend(["", "### X Citations"])
            for idx, citation in enumerate(citations, 1):
                title = citation.get("title") or citation.get("url")
                lines.append(f"{idx}. [{title}]({citation.get('url')})")
    graph = payload["graph"]
    metrics = graph.get("metrics", {})
    lines.extend(
        [
            "",
            "## Graph",
            f"- Nodes: {len(graph['nodes'])}",
            f"- Edges: {len(graph['edges'])}",
            f"- Metrics backend: {metrics.get('backend', 'unavailable')}",
            f"- NetworkX available: {metrics.get('networkx_available', False)}",
        ]
    )
    top_nodes = sorted(
        (node for node in graph["nodes"] if node.get("display", {}).get("visible_by_default", True)),
        key=lambda node: node.get("display", {}).get("score", 0),
        reverse=True,
    )[:5]
    if top_nodes:
        lines.extend(["", "## Top Graph Nodes"])
        for node in top_nodes:
            node_metrics = node.get("metrics", {})
            lines.append(
                f"- {node['label']} ({node['kind']}): degree={node_metrics.get('degree', 0)}, "
                f"pagerank={node_metrics.get('pagerank', 0.0):.6f}, component_size={node_metrics.get('component_size', 1)}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_graph_html(path: Path, graph_payload: dict[str, Any]) -> None:
    data = json.dumps(graph_payload, ensure_ascii=False)
    escaped = data.replace("</", "<\\/")
    document = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Graphify Local</title>
<style>
:root { color-scheme: dark; --bg:#030712; --panel:#0f172a; --panel2:#111827; --line:#374151; --muted:#9ca3af; --text:#f9fafb; --seed:#f59e0b; --note:#60a5fa; --topic:#34d399; --type:#a78bfa; --index:#f472b6; --meta:#94a3b8; }
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: var(--bg); color: var(--text); }
header { display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--line); background: rgba(15, 23, 42, .94); }
header small { color: var(--muted); }
#wrap { display: grid; grid-template-columns: minmax(0, 1fr) 380px; height: calc(100vh - 66px); }
#stage { position: relative; min-width: 0; }
svg { width: 100%; height: 100%; background: radial-gradient(circle at center, #1f2937 0, #111827 42%, #030712 100%); }
aside { overflow: auto; padding: 14px; border-left: 1px solid var(--line); background: var(--panel); }
.controls { display: grid; gap: 10px; margin-bottom: 14px; }
input[type="search"] { width: 100%; padding: 10px 11px; border: 1px solid var(--line); border-radius: 10px; background: #020617; color: var(--text); }
.filters { display: flex; flex-wrap: wrap; gap: 7px; }
.filter { display: inline-flex; align-items: center; gap: 5px; padding: 5px 8px; border: 1px solid var(--line); border-radius: 999px; background: var(--panel2); color: var(--muted); font-size: 12px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.stat { padding: 8px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel2); }
.stat strong { display:block; font-size: 18px; }
.stat small { color: var(--muted); }
.section-title { margin: 16px 0 8px; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.card { padding: 9px; margin: 7px 0; border: 1px solid var(--line); border-radius: 10px; background: rgba(17, 24, 39, .82); cursor: pointer; }
.card:hover, .card.selected { border-color: #60a5fa; background: rgba(30, 64, 175, .25); }
.card small, #detail small { color: var(--muted); }
.badge { display:inline-block; margin-right: 5px; padding: 2px 6px; border-radius: 999px; background:#1f2937; color:#cbd5e1; font-size: 11px; }
.edge { stroke: #64748b; stroke-opacity: .34; stroke-width: 1.1; }
.edge.connected { stroke: #fbbf24; stroke-opacity: .88; stroke-width: 2.2; }
.node { cursor: pointer; stroke: rgba(255,255,255,.72); stroke-width: 1; }
.node.dim { opacity: .24; }
.node.selected { stroke: #fef3c7; stroke-width: 3; }
.label { fill: #f8fafc; font-size: 11px; paint-order: stroke; stroke: rgba(3,7,18,.86); stroke-width: 3px; pointer-events: none; }
.label.dim { opacity: .3; }
.empty { color: var(--muted); padding: 16px; }
#legend { position: absolute; left: 14px; bottom: 14px; display:flex; gap: 8px; flex-wrap: wrap; max-width: calc(100% - 28px); }
.legend-item { padding: 5px 8px; border-radius: 999px; background: rgba(15,23,42,.78); border: 1px solid rgba(148,163,184,.35); color: #cbd5e1; font-size: 12px; }
@media (max-width: 900px) { #wrap { grid-template-columns: 1fr; height: auto; } #stage { height: 62vh; } aside { border-left: 0; border-top: 1px solid var(--line); } }
</style>
</head>
<body>
<header>
  <div><strong>Graphify Local</strong> <small>— hub-focused knowledge graph</small></div>
  <small id="queryLabel"></small>
</header>
<div id="wrap">
  <main id="stage">
    <svg id="graph" role="img" aria-label="Graphify Local knowledge graph"></svg>
    <div id="legend"></div>
  </main>
  <aside>
    <div class="controls">
      <input id="nodeSearch" type="search" placeholder="노드 검색: title, kind, id">
      <div id="kindFilters" class="filters" aria-label="Kind filters"></div>
    </div>
    <div class="stats">
      <div class="stat"><strong id="visibleCount">0</strong><small>visible</small></div>
      <div class="stat"><strong id="edgeCount">0</strong><small>edges</small></div>
      <div class="stat"><strong id="hiddenCount">0</strong><small>hidden</small></div>
    </div>
    <div class="section-title">Selected Node</div>
    <div id="detail" class="card"><small>노드를 클릭하면 연결과 메트릭을 보여줍니다.</small></div>
    <div class="section-title">Top Hubs</div>
    <div id="nodes"></div>
  </aside>
</div>
<script id="graph-data" type="application/json">__GRAPH_DATA__</script>
<script>
const payload = JSON.parse(document.getElementById('graph-data').textContent);
const graph = payload.graph || payload;
const nodes = (graph.nodes || []).map(node => ({...node}));
const edges = graph.edges || [];
const DEFAULT_MAX_VISIBLE = 80;
const colorByKind = {note:'#60a5fa', note_ref:'#38bdf8', topic:'#34d399', type:'#a78bfa', index:'#f472b6', x_post:'#f472b6', x_search:'#a78bfa'};
const svg = document.getElementById('graph');
const search = document.getElementById('nodeSearch');
const filterWrap = document.getElementById('kindFilters');
const detail = document.getElementById('detail');
const list = document.getElementById('nodes');
const selectedKinds = new Set();
let selectedId = null;

const byId = new Map(nodes.map(node => [node.id, node]));
const connectedById = new Map();
edges.forEach(edge => {
  if (!connectedById.has(edge.source)) connectedById.set(edge.source, []);
  if (!connectedById.has(edge.target)) connectedById.set(edge.target, []);
  connectedById.get(edge.source).push(edge);
  connectedById.get(edge.target).push(edge);
});

document.getElementById('queryLabel').textContent = payload.x_search ? `query: ${payload.query || ''} · Search X: ${payload.x_search.status}` : (payload.query ? `query: ${payload.query}` : 'metadata/wikilink graph');

function score(node) { return Number(node.display?.score || node.metrics?.pagerank || node.metrics?.degree_centrality || node.metrics?.degree || 0); }
function rank(node) { return Number(node.display?.rank || 999999); }
function color(node) { return node.seed ? '#f59e0b' : (colorByKind[node.kind] || '#94a3b8'); }
function labelOf(node) { return String(node.label || node.id || ''); }
function visibleDefault(node) { return Boolean(node.display?.visible_by_default || node.seed); }
function matchesSearch(node, term) {
  if (!term) return true;
  const haystack = `${node.label || ''} ${node.kind || ''} ${node.id || ''}`.toLowerCase();
  return haystack.includes(term);
}
function isConnectedToSelected(edge) { return selectedId && (edge.source === selectedId || edge.target === selectedId); }
function isNodeConnectedToSelected(node) {
  if (!selectedId || node.id === selectedId) return true;
  return (connectedById.get(selectedId) || []).some(edge => edge.source === node.id || edge.target === node.id);
}
function makeSvg(name, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  svg.appendChild(el);
  return el;
}
function setText(parent, text, tag = 'div', className = '') {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text;
  parent.appendChild(el);
  return el;
}
function sortedKinds() {
  return [...new Set(nodes.map(node => node.kind))].sort((a, b) => {
    const av = nodes.some(node => node.kind === a && visibleDefault(node)) ? 0 : 1;
    const bv = nodes.some(node => node.kind === b && visibleDefault(node)) ? 0 : 1;
    return av - bv || a.localeCompare(b);
  });
}
function initFilters() {
  sortedKinds().forEach(kind => {
    const checked = nodes.some(node => node.kind === kind && visibleDefault(node));
    if (checked) selectedKinds.add(kind);
    const label = document.createElement('label');
    label.className = 'filter';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = checked;
    input.addEventListener('change', () => {
      if (input.checked) selectedKinds.add(kind); else selectedKinds.delete(kind);
      render();
    });
    label.appendChild(input);
    label.appendChild(document.createTextNode(kind));
    filterWrap.appendChild(label);
  });
}
function visibleNodes() {
  const term = search.value.trim().toLowerCase();
  const base = nodes
    .filter(node => selectedKinds.has(node.kind))
    .filter(node => matchesSearch(node, term))
    .sort((a, b) => Number(b.seed) - Number(a.seed) || rank(a) - rank(b) || score(b) - score(a) || labelOf(a).localeCompare(labelOf(b)));
  if (term) return base.slice(0, DEFAULT_MAX_VISIBLE + 20);
  const seeds = base.filter(node => node.seed);
  const rest = base.filter(node => !node.seed).slice(0, Math.max(0, DEFAULT_MAX_VISIBLE - seeds.length));
  return [...seeds, ...rest];
}
function layout(current) {
  const width = svg.clientWidth || 900;
  const height = svg.clientHeight || 650;
  const cx = width / 2;
  const cy = height / 2;
  const baseRadius = Math.max(150, Math.min(width, height) * 0.36);
  const seeds = current.filter(node => node.seed);
  const hubs = current.filter(node => !node.seed).slice(0, 18);
  const outer = current.filter(node => !node.seed).slice(18);
  placeRing(seeds, cx, cy, Math.min(44, baseRadius * .18), -Math.PI / 2);
  placeRing(hubs, cx, cy, baseRadius * .55, -Math.PI / 2);
  placeRing(outer, cx, cy, baseRadius, -Math.PI / 2);
}
function placeRing(group, cx, cy, radius, startAngle) {
  if (group.length === 1) {
    group[0].x = cx;
    group[0].y = cy;
    return;
  }
  group.forEach((node, i) => {
    const angle = startAngle + (Math.PI * 2 * i) / Math.max(1, group.length);
    node.x = cx + Math.cos(angle) * radius;
    node.y = cy + Math.sin(angle) * radius;
  });
}
function render() {
  const current = visibleNodes();
  const currentIds = new Set(current.map(node => node.id));
  const currentEdges = edges.filter(edge => currentIds.has(edge.source) && currentIds.has(edge.target));
  layout(current);
  svg.replaceChildren();
  currentEdges.forEach(edge => {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (!source || !target) return;
    makeSvg('line', {x1:source.x, y1:source.y, x2:target.x, y2:target.y, class:`edge ${isConnectedToSelected(edge) ? 'connected' : ''}`});
  });
  current.forEach(node => {
    const dim = selectedId && !isNodeConnectedToSelected(node);
    const circle = makeSvg('circle', {
      cx:node.x, cy:node.y,
      r: Math.max(7, Math.min(18, 7 + Math.log2(1 + (node.metrics?.degree || 0)) * 2 + (node.seed ? 3 : 0))),
      fill: color(node),
      class: `node ${dim ? 'dim' : ''} ${node.id === selectedId ? 'selected' : ''}`,
      tabindex: '0'
    });
    circle.addEventListener('click', () => selectNode(node.id));
    const text = makeSvg('text', {x:node.x + 13, y:node.y + 4, class:`label ${dim ? 'dim' : ''}`});
    text.textContent = labelOf(node);
  });
  document.getElementById('visibleCount').textContent = String(current.length);
  document.getElementById('edgeCount').textContent = String(currentEdges.length);
  document.getElementById('hiddenCount').textContent = String(Math.max(0, nodes.length - current.length));
  renderList(current);
  renderLegend();
  if (selectedId && !currentIds.has(selectedId)) selectedId = null;
  renderDetail(selectedId ? byId.get(selectedId) : null);
}
function renderList(current) {
  list.replaceChildren();
  if (!current.length) {
    setText(list, '필터와 검색 조건에 맞는 노드가 없습니다.', 'div', 'empty');
    return;
  }
  current.slice(0, 30).forEach(node => {
    const card = document.createElement('div');
    card.className = `card ${node.id === selectedId ? 'selected' : ''}`;
    card.addEventListener('click', () => selectNode(node.id));
    setText(card, labelOf(node), 'strong');
    setText(card, `${node.kind} · rank ${node.display?.rank || '-'} · score ${score(node).toPrecision(3)}`, 'small');
    list.appendChild(card);
  });
}
function renderDetail(node) {
  detail.replaceChildren();
  if (!node) {
    setText(detail, '노드를 클릭하면 연결과 메트릭을 보여줍니다.', 'small');
    return;
  }
  setText(detail, labelOf(node), 'strong');
  const meta = document.createElement('div');
  ['seed', node.kind, node.display?.reason].filter(Boolean).forEach(value => {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = String(value);
    meta.appendChild(badge);
  });
  detail.appendChild(meta);
  setText(detail, node.id, 'small');
  const metrics = node.metrics || {};
  setText(detail, `degree ${metrics.degree || 0} · pagerank ${Number(metrics.pagerank || 0).toPrecision(3)} · component ${metrics.component_size || 1}`, 'small');
  const related = (connectedById.get(node.id) || []).slice(0, 8);
  if (related.length) setText(detail, 'Connections', 'div', 'section-title');
  related.forEach(edge => {
    const otherId = edge.source === node.id ? edge.target : edge.source;
    const other = byId.get(otherId);
    setText(detail, `${edge.relation} → ${other ? labelOf(other) : otherId}`, 'small');
  });
}
function renderLegend() {
  const legend = document.getElementById('legend');
  legend.replaceChildren();
  ['seed', ...sortedKinds().filter(kind => selectedKinds.has(kind)).slice(0, 8)].forEach(kind => {
    const item = document.createElement('span');
    item.className = 'legend-item';
    item.textContent = kind;
    legend.appendChild(item);
  });
}
function selectNode(id) {
  selectedId = selectedId === id ? null : id;
  render();
}
search.addEventListener('input', render);
window.addEventListener('resize', render);
initFilters();
render();
</script>
</body>
</html>
""".replace("__GRAPH_DATA__", escaped)
    path.write_text(document, encoding="utf-8")
