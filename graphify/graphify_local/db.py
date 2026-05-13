from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sqlite3
from typing import Iterable

from .parser import ParsedNote, as_list, label_from_wikilink, parse_note

METADATA_RELATIONS = {
    "topics": ("topic", "has_topic"),
    "tags": ("tag", "has_tag"),
    "type": ("type", "has_type"),
    "index": ("index", "indexed_under"),
    "author": ("author", "authored_by"),
    "status": ("status", "has_status"),
    "date": ("date", "has_date"),
}


def normalized(value: str) -> str:
    return " ".join(value.strip().lower().split())


def note_node_id(relative_path: str) -> str:
    return f"note:{relative_path}"


def typed_node_id(kind: str, label: str) -> str:
    return f"{kind}:{normalized(label)}"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS note_fts;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS notes;

        CREATE TABLE notes (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            frontmatter_json TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            modified_at REAL NOT NULL,
            content_hash TEXT NOT NULL
        );

        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            label TEXT NOT NULL,
            normalized_label TEXT NOT NULL
        );

        CREATE TABLE edges (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            provenance TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            PRIMARY KEY (source_id, target_id, relation, provenance)
        );

        CREATE VIRTUAL TABLE note_fts USING fts5(
            note_id UNINDEXED,
            title,
            summary,
            tags,
            topics,
            links
        );
        """
    )


def upsert_node(conn: sqlite3.Connection, node_id: str, kind: str, label: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO nodes(id, kind, label, normalized_label) VALUES (?, ?, ?, ?)",
        (node_id, kind, label, normalized(label)),
    )


def insert_edge(conn: sqlite3.Connection, source_id: str, target_id: str, relation: str, provenance: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO edges(source_id, target_id, relation, provenance, confidence) VALUES (?, ?, ?, ?, 1.0)",
        (source_id, target_id, relation, provenance),
    )


DEFAULT_EXCLUDE_DIRS = (".git", ".obsidian", ".omx", ".trash", ".pytest_cache", "graphify")


def discover_markdown(
    vault_root: Path,
    exclude_dirs: Iterable[str] = DEFAULT_EXCLUDE_DIRS,
    limit: int | None = None,
) -> list[Path]:
    excluded = set(exclude_dirs)
    paths: list[Path] = []
    for root, dirs, files in os.walk(vault_root, onerror=lambda _error: None):
        dirs[:] = sorted(name for name in dirs if name not in excluded)
        root_path = Path(root)
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = root_path / name
            parts = set(path.relative_to(vault_root).parts)
            if parts & excluded:
                continue
            paths.append(path)
            if limit is not None and len(paths) >= limit:
                return paths
    if paths:
        return paths
    return discover_markdown_with_find(vault_root, excluded, limit)


def discover_markdown_with_find(vault_root: Path, excluded: set[str], limit: int | None) -> list[Path]:
    try:
        proc = subprocess.Popen(
            ["find", str(vault_root), "-type", "f", "-name", "*.md"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []

    paths: list[Path] = []
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            path = Path(line.rstrip("\n"))
            try:
                parts = set(path.relative_to(vault_root).parts)
            except ValueError:
                parts = set(path.parts)
            if parts & excluded:
                continue
            paths.append(path)
            if limit is not None and len(paths) >= limit:
                proc.terminate()
                break
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
    return paths


def build_database(
    vault_root: Path,
    db_path: Path,
    limit: int | None = None,
    exclude_dirs: Iterable[str] = DEFAULT_EXCLUDE_DIRS,
) -> dict[str, int]:
    vault_root = vault_root.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    notes = [parse_note(path, vault_root) for path in discover_markdown(vault_root, exclude_dirs=exclude_dirs, limit=limit)]
    title_to_note_id = {note.title: note_node_id(note.relative_path) for note in notes}
    stem_to_note_id = {Path(note.relative_path).stem: note_node_id(note.relative_path) for note in notes}

    conn = connect(db_path)
    try:
        init_db(conn)
        for note in notes:
            source_id = note_node_id(note.relative_path)
            upsert_node(conn, source_id, "note", note.title)
            summary = "\n".join(as_list(note.frontmatter.get("summary")))
            status = ", ".join(as_list(note.frontmatter.get("status")))
            note_type = ", ".join(label_from_wikilink(v) for v in as_list(note.frontmatter.get("type")))
            date = ", ".join(label_from_wikilink(v) for v in as_list(note.frontmatter.get("date")))
            conn.execute(
                """
                INSERT INTO notes(id, path, title, frontmatter_json, summary, status, type, date, modified_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    note.relative_path,
                    note.title,
                    json.dumps(note.frontmatter, ensure_ascii=False, sort_keys=True),
                    summary,
                    status,
                    note_type,
                    date,
                    note.path.stat().st_mtime,
                    note.content_hash,
                ),
            )
            add_metadata_edges(conn, note, source_id)
            add_wikilink_edges(conn, note, source_id, title_to_note_id, stem_to_note_id)
            conn.execute(
                "INSERT INTO note_fts(note_id, title, summary, tags, topics, links) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    note.title,
                    summary,
                    " ".join(as_list(note.frontmatter.get("tags"))),
                    " ".join(label_from_wikilink(v) for v in as_list(note.frontmatter.get("topics"))),
                    " ".join(note.wikilinks),
                ),
            )
        conn.commit()
        return {
            "notes": len(notes),
            "nodes": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
            "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        }
    finally:
        conn.close()


def add_metadata_edges(conn: sqlite3.Connection, note: ParsedNote, source_id: str) -> None:
    for field, (kind, relation) in METADATA_RELATIONS.items():
        for raw in as_list(note.frontmatter.get(field)):
            label = label_from_wikilink(raw)
            if not label:
                continue
            target_id = typed_node_id(kind, label)
            upsert_node(conn, target_id, kind, label)
            insert_edge(conn, source_id, target_id, relation, f"frontmatter.{field}")


def add_wikilink_edges(
    conn: sqlite3.Connection,
    note: ParsedNote,
    source_id: str,
    title_to_note_id: dict[str, str],
    stem_to_note_id: dict[str, str],
) -> None:
    for label in note.wikilinks:
        target_id = title_to_note_id.get(label) or stem_to_note_id.get(label)
        kind = "note"
        if target_id is None:
            target_id = typed_node_id("note_ref", label)
            kind = "note_ref"
        upsert_node(conn, target_id, kind, label)
        if target_id != source_id:
            insert_edge(conn, source_id, target_id, "links_to", "body.wikilink")
