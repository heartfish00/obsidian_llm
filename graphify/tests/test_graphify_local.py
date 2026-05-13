from __future__ import annotations

from pathlib import Path
import json
import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphify_local.db import build_database, connect
from graphify_local.export import write_graph_html, write_json, write_query_markdown
from graphify_local.query import query_graph, search_notes
from graphify_local.search_x import attach_x_search_context, load_dotenv_if_present, search_x_posts, split_handles


class GraphifyLocalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_vault = ROOT / "tests" / "fixtures" / "vault"
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "vault_graph.sqlite"
        self.stats = build_database(self.fixture_vault, self.db_path)
        self.conn = connect(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_build_database_extracts_notes_nodes_edges(self) -> None:
        self.assertEqual(self.stats["notes"], 3)
        self.assertGreaterEqual(self.stats["nodes"], 8)
        self.assertGreaterEqual(self.stats["edges"], 12)
        self.assertEqual(self.stats["node_metrics"], self.stats["nodes"])
        self.assertIn(self.stats["metrics_backend"], {"networkx", "fallback"})
        provenance = {
            row[0]
            for row in self.conn.execute("SELECT DISTINCT provenance FROM edges")
        }
        self.assertIn("frontmatter.topics", provenance)
        self.assertIn("body.wikilink", provenance)

    def test_build_database_persists_graph_metrics(self) -> None:
        row = self.conn.execute(
            """
            SELECT node_metrics.degree, node_metrics.component_size, node_metrics.backend
            FROM node_metrics
            JOIN nodes ON nodes.id = node_metrics.node_id
            WHERE nodes.label = ?
            """,
            ("RAG 평가",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertGreater(row["degree"], 0)
        self.assertGreaterEqual(row["component_size"], 1)
        self.assertIn(row["backend"], {"networkx", "fallback"})

    def test_search_uses_fts_and_returns_ranked_notes(self) -> None:
        results = search_notes(self.conn, "RAG 평가", limit=3)
        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "RAG 평가")

    def test_query_graph_supports_one_and_two_hop(self) -> None:
        one = query_graph(self.conn, "RAG 평가", limit=1, hops=1)
        two = query_graph(self.conn, "RAG 평가", limit=1, hops=2)
        self.assertEqual(one["graph"]["hops"], 1)
        self.assertEqual(two["graph"]["hops"], 2)
        self.assertGreaterEqual(len(two["graph"]["nodes"]), len(one["graph"]["nodes"]))
        self.assertTrue(all("provenance" in edge for edge in two["graph"]["edges"]))
        self.assertIn(two["graph"]["metrics"]["backend"], {"networkx", "fallback"})
        self.assertTrue(all("metrics" in node for node in two["graph"]["nodes"]))
        self.assertTrue(all("display" in node for node in two["graph"]["nodes"]))
        self.assertTrue(all("score" in node["display"] for node in two["graph"]["nodes"]))

    def test_query_graph_marks_knowledge_nodes_visible_by_default(self) -> None:
        payload = query_graph(self.conn, "RAG 평가", limit=1, hops=1)
        by_kind = {node["kind"]: node for node in payload["graph"]["nodes"]}
        self.assertTrue(by_kind["note"]["display"]["visible_by_default"])
        self.assertTrue(by_kind["topic"]["display"]["visible_by_default"])
        self.assertTrue(by_kind["type"]["display"]["visible_by_default"])
        self.assertTrue(by_kind["index"]["display"]["visible_by_default"])
        self.assertFalse(by_kind["date"]["display"]["visible_by_default"])
        visible_ranks = [
            node["display"]["rank"]
            for node in payload["graph"]["nodes"]
            if node["display"]["visible_by_default"]
        ]
        self.assertTrue(all(isinstance(rank, int) for rank in visible_ranks))

    def test_query_graph_handles_legacy_db_without_metrics_tables(self) -> None:
        self.conn.execute("DROP TABLE node_metrics")
        self.conn.execute("DROP TABLE graph_meta")
        payload = query_graph(self.conn, "RAG 평가", limit=1, hops=1)
        self.assertEqual(payload["graph"]["metrics"]["backend"], "unavailable")
        self.assertTrue(payload["graph"]["nodes"])
        self.assertTrue(all(node["metrics"]["backend"] == "unavailable" for node in payload["graph"]["nodes"]))

    def test_exports_markdown_json_and_html(self) -> None:
        payload = query_graph(self.conn, "graph", limit=2, hops=2)
        out = Path(self.tmp.name) / "out"
        out.mkdir()
        write_json(out / "query-result.json", payload)
        write_json(out / "graph.json", payload["graph"])
        write_query_markdown(out / "query-result.md", payload)
        write_graph_html(out / "graph.html", payload)
        self.assertTrue((out / "query-result.json").exists())
        self.assertTrue((out / "graph.json").exists())
        self.assertTrue((out / "query-result.md").read_text(encoding="utf-8").startswith("# Query Result"))
        self.assertIn("Metrics backend", (out / "query-result.md").read_text(encoding="utf-8"))
        html = (out / "graph.html").read_text(encoding="utf-8")
        self.assertIn("Graphify Local", html)
        self.assertIn("hub-focused knowledge graph", html)
        self.assertIn("nodeSearch", html)
        self.assertIn("kindFilters", html)
        self.assertIn("Selected Node", html)
        parsed = json.loads((out / "graph.json").read_text(encoding="utf-8"))
        self.assertIn("nodes", parsed)
        self.assertIn("edges", parsed)

    def test_empty_query_is_safe(self) -> None:
        payload = query_graph(self.conn, "", limit=2, hops=1)
        self.assertEqual(len(payload["results"]), 2)

    def test_search_x_missing_key_is_structured_error(self) -> None:
        result = search_x_posts("RAG 평가", api_key="")
        self.assertEqual(result["status"], "missing_api_key")
        self.assertEqual(result["provider"], "xai.responses.x_search")
        self.assertEqual(result["citations"], [])

    def test_search_x_context_adds_external_graph_nodes(self) -> None:
        payload = query_graph(self.conn, "RAG 평가", limit=1, hops=1)
        augmented = attach_x_search_context(
            payload,
            {
                "enabled": True,
                "status": "ok",
                "provider": "xai.responses.x_search",
                "model": "grok-4.3",
                "summary": "X summary",
                "citations": [{"url": "https://x.com/example/status/1", "title": "Example post"}],
            },
        )
        self.assertIn("x_search", augmented)
        kinds = {node["kind"] for node in augmented["graph"]["nodes"]}
        self.assertIn("x_search", kinds)
        self.assertIn("x_post", kinds)
        self.assertTrue(
            any(edge["provenance"] == "xai.responses.x_search" for edge in augmented["graph"]["edges"])
        )

    def test_split_handles_normalizes_commas_and_at_prefixes(self) -> None:
        self.assertEqual(split_handles("@openai, xai ,, @karpathy"), ["openai", "xai", "karpathy"])

    def test_dotenv_loader_sets_missing_xai_key(self) -> None:
        previous_key = os.environ.pop("XAI_API_KEY", None)
        previous_cwd = os.getcwd()
        try:
            os.chdir(self.tmp.name)
            Path(".env").write_text("XAI_API_KEY=fake-test-key\n", encoding="utf-8")
            load_dotenv_if_present()
            self.assertEqual(os.environ.get("XAI_API_KEY"), "fake-test-key")
        finally:
            os.chdir(previous_cwd)
            if previous_key is None:
                os.environ.pop("XAI_API_KEY", None)
            else:
                os.environ["XAI_API_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
