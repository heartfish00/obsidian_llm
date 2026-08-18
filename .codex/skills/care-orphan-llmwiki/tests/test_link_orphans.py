from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "link_orphans.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("link_orphans", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["link_orphans"] = module
    spec.loader.exec_module(module)
    return module


def write_note(vault_root: Path, relative_path: str, content: str) -> Path:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return path


class MergeSharedBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_script_module()

    def test_stacked_duplicate_blocks_collapse_into_one(self) -> None:
        body = (
            "note text\n"
            "\n"
            "---\n"
            "🔗 **Shared Keywords:** [[a]]\n"
            "\n"
            "---\n"
            "🔗 **Shared Keywords:** [[b]], [[a]]\n"
        )
        merged = self.mod.merge_shared_block(body, "keywords", [], "\n")
        self.assertEqual(
            merged,
            "note text\n\n---\n🔗 **Shared Keywords:** [[a]], [[b]]\n",
        )

    def test_variant_label_formats_are_detected_and_merged(self) -> None:
        body = (
            "text\n"
            "\n"
            "---\n"
            "🔗️ **Shared Keywords:** [[a]]\n"
            "\n"
            "---\n"
            "**shared keywords** [[b]]\n"
        )
        merged = self.mod.merge_shared_block(body, "keywords", [], "\n")
        self.assertEqual(merged.count("**Shared Keywords:**"), 1)
        self.assertIn("[[a]]", merged)
        self.assertIn("[[b]]", merged)

    def test_self_links_are_dropped(self) -> None:
        body = "text\n\n---\n🔗 **Shared Keywords:** [[self note]], [[other]]\n"
        merged = self.mod.merge_shared_block(body, "keywords", [], "\n", self_keys={"self note"})
        self.assertNotIn("[[self note]]", merged)
        self.assertIn("[[other]]", merged)

    def test_bare_and_bracketed_links_deduplicate(self) -> None:
        # Existing links are read bare from block lines while new links arrive as
        # [[x]] wikilinks; both must dedupe onto a single [[x]] entry.
        body = "text\n\n---\n🔗 **Shared Keywords:** [[x]]\n"
        merged = self.mod.merge_shared_block(body, "keywords", ["[[x]]", "[[y]]"], "\n")
        self.assertEqual(merged, "text\n\n---\n🔗 **Shared Keywords:** [[x]], [[y]]\n")

    def test_body_without_blocks_is_untouched(self) -> None:
        body = "plain body\nwith text\n"
        self.assertEqual(self.mod.merge_shared_block(body, "keywords", [], "\n"), body)

    def test_bracket_named_targets_still_merge(self) -> None:
        # Targets whose own name starts with "[" serialize as [[[name]]], which
        # WIKILINK_RE cannot parse; the fallback matcher must still merge them.
        block_line = "🔗 **Shared Keywords:** [[[연계세미나] 노트]]\n"
        body = "text\n\n---\n" + block_line + "\n---\n" + block_line
        merged = self.mod.merge_shared_block(body, "keywords", [], "\n")
        self.assertEqual(merged.count("Shared Keywords"), 1)
        self.assertIn("[[[연계세미나] 노트]]", merged)

    def test_prose_mention_is_not_a_block(self) -> None:
        body = (
            "- Find backlink candidates by shared keywords and existing-body-link exclusion.\n"
            "\n"
            "---\n"
            "🔗 **Shared Keywords:** [[a]]\n"
        )
        merged = self.mod.merge_shared_block(body, "keywords", [], "\n")
        self.assertIn("by shared keywords and", merged)
        self.assertEqual(merged.count("**Shared Keywords:** [[a]]"), 1)


class LinkOrphansCliTests(unittest.TestCase):
    def run_cli(self, vault_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT_PATH), "--vault", str(vault_root), *args]
        return subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")

    def test_target_scope_keeps_global_backlink_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/AI Target.md",
                """
                ---
                tags:
                  - AI
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/AI Candidate.md",
                """
                ---
                tags:
                  - AI
                ---
                candidate body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/Other.md",
                """
                ---
                tags:
                  - Finance
                ---
                other body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(
                vault_root,
                "--mode",
                "preview",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--report-json",
                str(report_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["scanned_notes"], 3)
            self.assertEqual(len(report["proposals"]), 1)
            self.assertEqual(report["proposals"][0]["path"], "PARA_1Projects/AI Target.md")
            self.assertEqual(
                report["proposals"][0]["backlink_targets"],
                [
                    {
                        "path": "PARA_3Resources/AI Candidate",
                        "shared_core_keywords": ["ai"],
                        "shared_authors": [],
                    }
                ],
            )

    def test_apply_only_writes_target_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            target_path = write_note(
                vault_root,
                "PARA_1Projects/AI Target.md",
                """
                ---
                tags:
                  - AI
                ---
                target body
                """,
            )
            candidate_path = write_note(
                vault_root,
                "PARA_3Resources/AI Candidate.md",
                """
                ---
                tags:
                  - AI
                ---
                candidate body
                """,
            )

            result = self.run_cli(
                vault_root,
                "--mode",
                "apply",
                "--target-path-glob",
                "PARA_1Projects/*",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            target_text = target_path.read_text(encoding="utf-8")
            candidate_text = candidate_path.read_text(encoding="utf-8")
            self.assertIn("[[AI Candidate]]", target_text)
            self.assertNotIn("Shared Keywords", candidate_text)
            self.assertNotIn("Shared Authors", candidate_text)

    def test_preview_link_limit_summarizes_extra_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/AI Target.md",
                """
                ---
                tags:
                  - AI
                ---
                target body
                """,
            )
            for index in range(5):
                write_note(
                    vault_root,
                    f"PARA_3Resources/AI Candidate {index}.md",
                    f"""
                    ---
                    tags:
                      - AI
                    ---
                    candidate {index}
                    """,
                )

            result = self.run_cli(
                vault_root,
                "--mode",
                "preview",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--preview-link-limit",
                "2",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("... (+3 more)", result.stdout)

    def test_core_shared_keywords_only_use_title_words(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/Claude Agent Playbook.md",
                """
                ---
                tags:
                  - Claude
                  - Agent
                  - Notes
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/Claude Workflow.md",
                """
                ---
                tags:
                  - Claude
                ---
                candidate 1
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/Agent Ops.md",
                """
                ---
                tags:
                  - Agent
                ---
                candidate 2
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/Reference Archive.md",
                """
                ---
                tags:
                  - Notes
                ---
                candidate 3
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(vault_root, "--mode", "preview", "--report-json", str(report_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            proposal = next(item for item in report["proposals"] if item["path"] == "PARA_1Projects/Claude Agent Playbook.md")
            self.assertEqual(proposal["core_shared_keywords"], ["claude", "agent"])
            self.assertEqual(
                [item["path"] for item in proposal["backlink_targets"]],
                ["PARA_3Resources/Agent Ops", "PARA_3Resources/Claude Workflow"],
            )
            self.assertNotIn("PARA_3Resources/Reference Archive", json.dumps(proposal, ensure_ascii=False))

    def test_authur_input_is_normalized_to_author_and_adds_author_backlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            target_path = write_note(
                vault_root,
                "PARA_1Projects/No Keyword Match.md",
                """
                ---
                authur: "Google Docs"
                tags:
                  - Archive
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/Candidate.md",
                """
                ---
                author: "Google Docs"
                tags:
                  - Different
                ---
                candidate body
                """,
            )

            result = self.run_cli(
                vault_root,
                "--mode",
                "apply",
                "--target-path-glob",
                "PARA_1Projects/*",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            target_text = target_path.read_text(encoding="utf-8")
            self.assertIn("author:", target_text)
            self.assertNotIn("authur:", target_text)
            self.assertIn("Google Docs", target_text)
            self.assertIn("[[Candidate]]", target_text)
            self.assertIn("Shared Authors", target_text)

    def test_empty_keywords_gets_title_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/DB Design.md",
                """
                ---
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/DB Patterns.md",
                """
                ---
                tags:
                  - DB
                ---
                candidate body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(
                vault_root,
                "--mode",
                "preview",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--report-json",
                str(report_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report["proposals"]), 1)
            proposal = report["proposals"][0]
            self.assertEqual(proposal["path"], "PARA_1Projects/DB Design.md")
            self.assertIn("db", proposal["core_shared_keywords"])
            self.assertTrue(
                any("DB Patterns" in t["path"] for t in proposal["backlink_targets"]),
                f"Expected DB Patterns in backlinks, got: {proposal['backlink_targets']}",
            )

    def test_author_ref_matches_body_wikilink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            target_path = write_note(
                vault_root,
                "PARA_1Projects/My Note.md",
                """
                ---
                ---
                Some content

                - [[테디노트 teddynote 이경록]]
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/author_ref.md",
                """
                ---
                AUTHOR:
                  - "[[테디노트 teddynote 이경록]]"
                ---
                ref body
                """,
            )

            result = self.run_cli(
                vault_root,
                "--mode",
                "apply",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--author-ref",
                "PARA_3Resources/author_ref.md",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            target_text = target_path.read_text(encoding="utf-8")
            self.assertIn("author:", target_text)
            self.assertIn("테디노트 teddynote 이경록", target_text)

    def test_author_ref_matches_title_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            target_path = write_note(
                vault_root,
                "PARA_1Projects/빅쿼리 활용법.md",
                """
                ---
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/author_ref.md",
                """
                ---
                AUTHOR:
                  - "[[빅쿼리]]"
                ---
                ref body
                """,
            )

            result = self.run_cli(
                vault_root,
                "--mode",
                "apply",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--author-ref",
                "PARA_3Resources/author_ref.md",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            target_text = target_path.read_text(encoding="utf-8")
            self.assertIn("author:", target_text)
            self.assertIn("빅쿼리", target_text)

    def test_non_para_folders_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/AI Note.md",
                """
                ---
                tags:
                  - AI
                ---
                para body
                """,
            )
            write_note(
                vault_root,
                "Chats/Chat Note.md",
                """
                ---
                tags:
                  - AI
                ---
                chat body
                """,
            )
            write_note(
                vault_root,
                "Clippings/Clip Note.md",
                """
                ---
                tags:
                  - AI
                ---
                clip body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(vault_root, "--mode", "preview", "--report-json", str(report_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["scanned_notes"], 1)
            paths_in_output = result.stdout
            self.assertIn("AI Note", paths_in_output)
            self.assertNotIn("Chat Note", paths_in_output)
            self.assertNotIn("Clip Note", paths_in_output)

    def test_excluded_file_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_3Resources/2024/그루,구루 대분류 AI.md",
                """
                ---
                tags:
                  - AI
                ---
                excluded body
                """,
            )
            write_note(
                vault_root,
                "PARA_1Projects/AI Note.md",
                """
                ---
                tags:
                  - AI
                ---
                normal body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(vault_root, "--mode", "preview", "--report-json", str(report_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            scanned_paths = [p for p in result.stdout.splitlines() if ".md" in p]
            for line in scanned_paths:
                self.assertNotIn("그루,구루 대분류 AI", line)

    def test_root_md_files_are_included(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "RootNote.md",
                """
                ---
                tags:
                  - AI
                ---
                root body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/AI Match.md",
                """
                ---
                tags:
                  - AI
                ---
                para body
                """,
            )
            write_note(
                vault_root,
                "Chats/Chat Note.md",
                """
                ---
                tags:
                  - AI
                ---
                chat body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(vault_root, "--mode", "preview", "--report-json", str(report_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["scanned_notes"], 2)
            self.assertNotIn("Chat Note", result.stdout)

    def test_author_ref_priority_over_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            target_path = write_note(
                vault_root,
                "PARA_1Projects/My Project.md",
                """
                ---
                url: https://www.example.com/page
                ---
                - [[케인]]

                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/author_ref.md",
                """
                ---
                AUTHOR:
                  - "[[모두의 AI 케인]]"
                ---
                ref body
                """,
            )

            report_path = vault_root / "report.json"
            result = self.run_cli(
                vault_root,
                "--mode",
                "preview",
                "--target-path-glob",
                "PARA_1Projects/*",
                "--author-ref",
                "PARA_3Resources/author_ref.md",
                "--report-json",
                str(report_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(len(report["proposals"]) >= 1)
            proposal = report["proposals"][0]
            self.assertEqual(proposal["author_candidate"], "모두의 AI 케인")


    def test_cli_apply_twice_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            write_note(
                vault_root,
                "PARA_1Projects/AI Target.md",
                """
                ---
                tags:
                  - AI
                ---
                target body
                """,
            )
            write_note(
                vault_root,
                "PARA_3Resources/AI Candidate.md",
                """
                ---
                tags:
                  - AI
                ---
                candidate body
                """,
            )

            first = self.run_cli(vault_root, "--mode", "apply", "--yes")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("applied: 2", first.stdout)

            second = self.run_cli(vault_root, "--mode", "apply", "--yes")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Candidate notes with changes: 0", second.stdout)

    def test_cli_consolidate_only_merges_and_preserves_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            frontmatter = "tags:\n  - AI\ncore_shared_keywords:\n  - ai\n"
            content = (
                "---\n"
                + frontmatter
                + "---\n"
                + "body\n"
                + "\n"
                + "---\n"
                + "🔗 **Shared Keywords:** [[first note]]\n"
                + "\n"
                + "---\n"
                + "🔗 **Shared Keywords:** [[second note]]\n"
            )
            path = write_note(vault_root, "PARA_1Projects/Dup Note.md", content)

            result = self.run_cli(vault_root, "--consolidate-only", "--mode", "apply", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = path.read_text(encoding="utf-8")
            self.assertTrue(updated.startswith("---\n" + frontmatter + "---\n"), updated)
            self.assertEqual(updated.count("**Shared Keywords:**"), 1)
            self.assertIn("[[first note]]", updated)
            self.assertIn("[[second note]]", updated)

            second = self.run_cli(vault_root, "--consolidate-only", "--mode", "apply", "--yes")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Candidate notes with changes: 0", second.stdout)


if __name__ == "__main__":
    unittest.main()
