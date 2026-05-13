from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "link_orphans.py"


def write_note(vault_root: Path, relative_path: str, content: str) -> Path:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return path


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


if __name__ == "__main__":
    unittest.main()
