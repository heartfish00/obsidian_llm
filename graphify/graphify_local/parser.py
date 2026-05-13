from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import re
from typing import Any

WIKILINK_RE = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


@dataclass
class ParsedNote:
    path: Path
    relative_path: str
    title: str
    frontmatter: dict[str, Any]
    body: str
    wikilinks: list[str] = field(default_factory=list)
    content_hash: str = ""


def normalize_key(key: str) -> str:
    key = key.strip().strip('"').strip("'")
    if key.endswith(":"):
        key = key[:-1]
    return key.strip().lower()


def clean_scalar(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value.strip()


def label_from_wikilink(value: str) -> str:
    match = WIKILINK_RE.search(value)
    if match:
        return match.group(1).strip()
    return clean_scalar(value)


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [clean_scalar(str(item)) for item in value if clean_scalar(str(item))]
    if isinstance(value, str):
        stripped = clean_scalar(value)
        return [stripped] if stripped else []
    return [str(value)]


def split_frontmatter_key(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith(('"', "'")):
        quote = stripped[0]
        end = stripped.find(quote, 1)
        if end != -1 and stripped[end + 1 :].startswith(":"):
            return stripped[1:end], stripped[end + 2 :].strip()
    if ":" not in stripped:
        return None
    key, value = stripped.split(":", 1)
    return key.strip(), value.strip()


def parse_simple_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].splitlines()
    body = text[end + len("\n---") :].lstrip("\n")
    data: dict[str, Any] = {}
    i = 0
    while i < len(raw):
        line = raw[i]
        parsed = split_frontmatter_key(line)
        if parsed is None:
            i += 1
            continue
        key, value = parsed
        norm = normalize_key(key)
        if value in {"", "[]"}:
            items: list[str] = []
            i += 1
            while i < len(raw) and (raw[i].startswith(" ") or raw[i].startswith("\t")):
                item = raw[i].strip()
                if item.startswith("-"):
                    items.append(clean_scalar(item[1:].strip()))
                elif item:
                    items.append(clean_scalar(item))
                i += 1
            data[norm] = items
            continue
        if value.startswith("|") or value.startswith(">"):
            block: list[str] = []
            i += 1
            while i < len(raw) and (raw[i].startswith(" ") or raw[i].startswith("\t")):
                block.append(raw[i].strip())
                i += 1
            data[norm] = "\n".join(block)
            continue
        data[norm] = clean_scalar(value)
        i += 1
    return data, body


def title_from_body_or_path(body: str, path: Path) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    return path.stem


def parse_note(path: Path, vault_root: Path) -> ParsedNote:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_simple_frontmatter(text)
    title = title_from_body_or_path(body, path)
    relative_path = path.relative_to(vault_root).as_posix()
    wikilinks = sorted({match.group(1).strip() for match in WIKILINK_RE.finditer(body)})
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return ParsedNote(path, relative_path, title, frontmatter, body, wikilinks, digest)
