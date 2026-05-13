from __future__ import annotations

from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphify_local.db import build_database, connect
from graphify_local.export import write_graph_html, write_json, write_query_markdown
from graphify_local.query import query_graph, search_notes


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
        provenance = {
            row[0]
            for row in self.conn.execute("SELECT DISTINCT provenance FROM edges")
        }
        self.assertIn("frontmatter.topics", provenance)
        self.assertIn("body.wikilink", provenance)

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
        self.assertIn("Graphify Local", (out / "graph.html").read_text(encoding="utf-8"))
        parsed = json.loads((out / "graph.json").read_text(encoding="utf-8"))
        self.assertIn("nodes", parsed)
        self.assertIn("edges", parsed)

    def test_empty_query_is_safe(self) -> None:
        payload = query_graph(self.conn, "", limit=2, hops=1)
        self.assertEqual(len(payload["results"]), 2)


if __name__ == "__main__":
    unittest.main()
