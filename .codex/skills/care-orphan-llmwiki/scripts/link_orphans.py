#!/usr/bin/env python
from __future__ import annotations

import argparse
import fnmatch
import io
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

try:
    from ruamel.yaml import YAML
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "ruamel.yaml is required. Install it first, for example: pip install ruamel.yaml"
    ) from exc

YAML_PARSER = YAML()
YAML_PARSER.preserve_quotes = True
YAML_PARSER.width = 4096
YAML_PARSER.indent(mapping=2, sequence=4, offset=2)

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
URL_RE = re.compile(r"https?://\S+")
SHARED_BLOCK_LABEL = "🔗 **Shared Keywords:**"
SHARED_AUTHOR_BLOCK_LABEL = "🔗 **Shared Authors:**"
SHARED_BLOCK_KIND_KEYWORDS = "keywords"
SHARED_BLOCK_KIND_AUTHORS = "authors"
SHARED_BLOCK_KIND_LABELS = {
    SHARED_BLOCK_KIND_KEYWORDS: SHARED_BLOCK_LABEL,
    SHARED_BLOCK_KIND_AUTHORS: SHARED_AUTHOR_BLOCK_LABEL,
}
# Tolerant matcher for shared-block lines: optional 🔗 (+ variation selector),
# optional/misplaced bold markers, flexible spacing, case-insensitive. Whatever
# follows the label must be empty or start with a wikilink, so prose that merely
# mentions "shared keywords" is never mistaken for a block.
SHARED_BLOCK_LINE_RE = re.compile(
    r"^\s*(?:\U0001F517️?\s*)?\*{0,2}\s*shared\s+(keywords|authors)\s*[:：*]{0,4}\s*(.*)$",
    re.IGNORECASE,
)
# Lenient fallback for links WIKILINK_RE cannot parse, e.g. targets whose own
# name starts with "[" ("[연계세미나] ...") which serialize as [[[name]]].
# The lazy opener keeps exactly two "[" so the target's own leading "[" survives.
FALLBACK_BLOCK_LINK_RE = re.compile(r"\[{2,}?(.*?)\]{2,}")
CORE_SHARED_KEYWORDS_FIELD = "core_shared_keywords"
TITLE_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
CORE_SHARED_KEYWORD_STOPWORDS = frozenset({
    # 사용자 지정
    "오픈소스", "open", "source", "saas", "ai", "digital", "data",
    "claude", "code", "model", "gpt", "chatgpt", "지피티", "모델",
    "클로드", "gemini", "google",
    # 초범용어
    "to", "by", "에서", "만들기", "생성", "공개", "가능", "기능",
    "활용", "vs", "on", "서비스", "무료", "도구",
    # 연도 (2000-2099 범위)
    "2024", "2025", "2026", "2027", "2028", "2029",
    "2024년", "2025년", "2026년", "2027년", "2028년", "2029년",
    # AI/LLM 범용어
    "llm", "mcp", "agent", "에이전트", "프롬프트",
    "openai", "codex", "rag", "skills", "cli", "api",
    # 범용 기술어
    "이미지", "image", "pdf", "데이터", "코드", "영상",
    "video", "파일", "설치", "유튜브", "파이썬", "자동화",
    "분석", "ui", "디자인", "템플릿", "template",
    # 노이즈 — 기본 제목 / URL 잔여
    "무제", "untitled", "com",
    # 영문 누락 보완 (한국어 스톱워드의 영문 쌍)
    "opensource", "design", "python",
    # dev 범용어
    "github", "git", "plugin", "json", "html", "css",
    "sql", "frontend", "workflow", "ide", "windows",
    # vault 문맥 범용어
    "obsidian", "ppt", "gpu",
    # 기술 약어/포맷
    "wsl", "ocr", "tts", "lora", "vllm", "stt", "cuda", "vram",
    # 초범용어 추가
    "subagent", "promptengineering", "논문", "특강", "생성형",
    "db", "cloud", "www",
})
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}년?$")
CORE_SHARED_KEYWORD_MAX_MATCHES = 50
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".obsidian",
    ".codex",
    ".omc",
    ".omx",
    ".trash",
    "__pycache__",
    "node_modules",
}

DEFAULT_EXCLUDED_FILES = {
    "그루,구루 대분류 AI.md",
}


def build_include_patterns(vault_root: Path) -> list[str]:
    """PARA_* 하위 .md만 처리하도록 include 패턴을 생성. 루트 .md는 별도 처리."""
    patterns: list[str] = []
    for entry in sorted(vault_root.iterdir()):
        if entry.is_dir() and entry.name.startswith("PARA") and not entry.name.startswith("."):
            patterns.append(f"{entry.name}/**.md")
    return patterns


@dataclass
class ParsedNote:
    path: Path
    relative_path: Path
    newline: str
    raw_text: str
    body: str
    frontmatter_text: str | None
    metadata: Any | None
    keywords: list[str] = field(default_factory=list)
    core_shared_keywords: list[str] = field(default_factory=list)
    existing_links: set[str] = field(default_factory=set)
    source_url: str | None = None
    author_values: list[str] = field(default_factory=list)
    author_value: str | None = None
    parse_error: str | None = None

    @property
    def title(self) -> str:
        return self.relative_path.stem

    @property
    def wikilink_target(self) -> str:
        relative_no_suffix = self.relative_path.with_suffix("")
        return relative_no_suffix.as_posix()

    @property
    def wikilink(self) -> str:
        return f"[[{self.relative_path.stem}]]"

    @property
    def link_keys(self) -> set[str]:
        return {
            normalize_link_key(self.wikilink_target),
            normalize_link_key(self.relative_path.stem),
        }


@dataclass
class BacklinkTarget:
    note: ParsedNote
    shared_core_keywords: list[str] = field(default_factory=list)
    shared_authors: list[str] = field(default_factory=list)

    @property
    def has_keyword_match(self) -> bool:
        return bool(self.shared_core_keywords)

    @property
    def has_author_match(self) -> bool:
        return bool(self.shared_authors)

    @property
    def score(self) -> int:
        return len(self.shared_core_keywords) + len(self.shared_authors)


@dataclass
class NoteProposal:
    note: ParsedNote
    author_candidate: str | None
    backlink_targets: list[BacklinkTarget]
    core_shared_keywords_changed: bool = False
    author_field_normalization_needed: bool = False
    needs_block_consolidation: bool = False
    consolidation_only: bool = False

    @property
    def keyword_backlink_targets(self) -> list[BacklinkTarget]:
        return [target for target in self.backlink_targets if target.has_keyword_match]

    @property
    def author_backlink_targets(self) -> list[BacklinkTarget]:
        return [target for target in self.backlink_targets if target.has_author_match]

    @property
    def body_author_backlink_targets(self) -> list[BacklinkTarget]:
        return [
            target for target in self.backlink_targets if target.has_author_match and not target.has_keyword_match
        ]

    @property
    def has_changes(self) -> bool:
        return bool(
            self.author_candidate
            or self.backlink_targets
            or self.core_shared_keywords_changed
            or self.author_field_normalization_needed
            or self.needs_block_consolidation
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find orphan Obsidian notes and safely repair author/backlink gaps without LLM calls."
    )
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault root")
    parser.add_argument(
        "--mode",
        choices=["interactive", "preview", "apply"],
        default="interactive",
        help="interactive: prompt per note, preview: no writes, apply: write without prompts",
    )
    parser.add_argument("--yes", action="store_true", help="Alias for --mode apply")
    parser.add_argument(
        "--consolidate-only",
        action="store_true",
        help="Only merge existing duplicate shared blocks; no new backlinks or metadata changes",
    )
    parser.add_argument("--limit", type=int, help="Only process the first N parsed markdown notes")
    parser.add_argument(
        "--path-glob",
        action="append",
        default=[],
        help="Only include markdown files whose vault-relative path matches this glob. Repeatable.",
    )
    parser.add_argument(
        "--target-path-glob",
        action="append",
        default=[],
        help="Only notes whose vault-relative path matches this glob are eligible for changes. Repeatable.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Extra directory names to skip while scanning. Repeatable.",
    )
    parser.add_argument(
        "--author-min-length",
        type=int,
        default=2,
        help="Treat author values with this many characters or fewer as missing",
    )
    parser.add_argument(
        "--max-backlinks",
        type=int,
        default=None,
        help="Optional cap for appended backlink candidates per note",
    )
    parser.add_argument(
        "--report-json",
        help="Optional path to write a JSON summary report",
    )
    parser.add_argument(
        "--preview-link-limit",
        type=int,
        default=20,
        help="Limit backlink preview output per note; 0 shows all",
    )
    parser.add_argument(
        "--preview-error-limit",
        type=int,
        default=10,
        help="Limit parse error preview output; 0 shows all",
    )
    parser.add_argument(
        "--author-ref",
        action="append",
        default=[],
        help="Reference note path(s) whose AUTHOR field lists known authors. Repeatable.",
    )
    return parser.parse_args()


def normalize_keyword(value: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        return ""
    if cleaned.startswith("#"):
        cleaned = cleaned[1:]
    return cleaned.casefold()


def normalize_link_key(value: str) -> str:
    text = str(value).strip().replace("\\", "/")
    text = text.split("|", 1)[0].split("#", 1)[0].strip()
    if text.endswith(".md"):
        text = text[:-3]
    if text.startswith("./"):
        text = text[2:]
    return text.casefold()


def iter_strings(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            if item is None:
                continue
            result.extend(iter_strings(item))
        return result
    return [str(value)]


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---"):
        return None, text
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if match:
        return match.group(1), text[match.end() :]
    # Handle empty frontmatter: ---\n---\n
    empty_match = re.match(r"^---\r?\n---\r?\n?", text)
    if empty_match:
        return "", text[empty_match.end() :]
    return None, text


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def tokenize_title(title: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for match in TITLE_TOKEN_RE.findall(title.casefold()):
        token = match.strip()
        if len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def collect_core_shared_keywords(title: str, keywords: list[str]) -> list[str]:
    title_tokens = set(tokenize_title(title))
    result: list[str] = []
    for keyword in keywords:
        if _YEAR_RE.match(keyword):
            continue
        if keyword in title_tokens:
            result.append(keyword)
            continue
        if keyword in CORE_SHARED_KEYWORD_STOPWORDS:
            continue
        for token in title_tokens:
            if token in CORE_SHARED_KEYWORD_STOPWORDS or _YEAR_RE.match(token):
                continue
            if len(token) >= 2 and (token in keyword or keyword in token):
                result.append(keyword if len(keyword) >= len(token) else token)
                break
    return result


def normalize_author_key(value: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        return ""
    if cleaned.startswith("[[") and cleaned.endswith("]]"):
        return ""
    return cleaned.casefold()


def collect_author_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for field_name in ("author", "authur"):
        for item in iter_strings(metadata.get(field_name)):
            stripped = str(item).strip()
            normalized = normalize_author_key(stripped)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            values.append(stripped)
    return values


def load_author_refs(ref_paths: list[str], vault_root: Path) -> dict[str, str]:
    """Parse reference notes, return {normalized_author_key: raw_author_value}."""
    ref_authors: dict[str, str] = {}
    for ref_path_str in ref_paths:
        ref_path = vault_root / ref_path_str
        if not ref_path.exists():
            print(f"Warning: author-ref not found: {ref_path}", file=sys.stderr)
            continue
        try:
            raw = ref_path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Warning: cannot read author-ref {ref_path}: {exc}", file=sys.stderr)
            continue
        fm_text, _ = split_frontmatter(raw)
        if fm_text is None:
            continue
        try:
            metadata = YAML_PARSER.load(fm_text) or {}
        except Exception:
            continue
        if not isinstance(metadata, dict):
            continue
        for key, value in metadata.items():
            if "author" not in str(key).lower():
                continue
            for item in iter_strings(value):
                stripped = str(item).strip()
                m = re.match(r"^\[\[(.+)\]\]$", stripped)
                raw_value = m.group(1).strip() if m else stripped
                normalized = raw_value.casefold()
                if normalized and normalized not in ref_authors:
                    ref_authors[normalized] = raw_value
    return ref_authors


def match_author_from_ref(note: ParsedNote, ref_authors: dict[str, str]) -> str | None:
    """Match author from reference file via body wikilinks and title tokens."""
    if not ref_authors:
        return None
    # 1. Body wikilink matching (exact key)
    for link_key in note.existing_links:
        if link_key in ref_authors:
            return ref_authors[link_key]
    # 2. Body wikilink matching (token overlap with ref author names)
    for link_key in note.existing_links:
        link_tokens = set(tokenize_title(link_key))
        if not link_tokens:
            continue
        for ref_key, ref_value in ref_authors.items():
            ref_tokens = set(tokenize_title(ref_value))
            if link_tokens & ref_tokens:
                return ref_value
    # 3. Title token matching (tokenize ref author names, check overlap)
    title_tokens = set(tokenize_title(note.title))
    for ref_key, ref_value in ref_authors.items():
        ref_tokens = set(tokenize_title(ref_value))
        if title_tokens & ref_tokens:
            return ref_value
    return None


def path_matches_globs(relative_path: Path, path_globs: list[str]) -> bool:
    if not path_globs:
        return True
    relative_posix = relative_path.as_posix()
    return any(fnmatch.fnmatch(relative_posix, pattern) for pattern in path_globs)


def should_skip_path(
    relative_path: Path,
    exclude_dirs: set[str],
    path_globs: list[str],
    include_patterns: list[str] | None = None,
) -> bool:
    if relative_path.name in DEFAULT_EXCLUDED_FILES:
        return True
    is_root_file = len(relative_path.parts) == 1
    if include_patterns and not is_root_file and not path_matches_globs(relative_path, include_patterns):
        return True
    parts = set(relative_path.parts[:-1])
    for part in parts:
        if part in exclude_dirs or part.startswith("."):
            return True
    return not path_matches_globs(relative_path, path_globs)


def parse_note(path: Path, vault_root: Path) -> ParsedNote:
    raw_text = path.read_text(encoding="utf-8")
    newline = detect_newline(raw_text)
    frontmatter_text, body = split_frontmatter(raw_text)
    note = ParsedNote(
        path=path,
        relative_path=path.relative_to(vault_root),
        newline=newline,
        raw_text=raw_text,
        body=body,
        frontmatter_text=frontmatter_text,
        metadata=None,
    )
    note.existing_links = {normalize_link_key(match) for match in WIKILINK_RE.findall(body)}

    if raw_text.startswith("---") and frontmatter_text is None:
        note.parse_error = "Unterminated frontmatter block"
        return note

    if frontmatter_text is None:
        note.keywords = tokenize_title(note.title)
        note.core_shared_keywords = collect_core_shared_keywords(note.title, note.keywords)
        return note

    try:
        note.metadata = YAML_PARSER.load(frontmatter_text) or {}
    except Exception as exc:
        note.parse_error = str(exc)
        return note

    if not isinstance(note.metadata, dict):
        note.parse_error = f"Frontmatter is not a mapping: {type(note.metadata).__name__}"
        note.metadata = None
        return note

    note.keywords = collect_keywords(note.metadata)
    if not note.keywords:
        note.keywords = tokenize_title(note.title)
    note.core_shared_keywords = collect_core_shared_keywords(note.title, note.keywords)
    note.source_url = first_url_from_metadata(note.metadata)
    note.author_values = collect_author_values(note.metadata)
    note.author_value = normalize_author_value(note.author_values)
    return note


def collect_keywords(metadata: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for field_name in ("keywords", "tags"):
        for item in iter_strings(metadata.get(field_name)):
            normalized = normalize_keyword(item)
            if normalized and normalized not in seen:
                seen.add(normalized)
                keywords.append(normalized)
    return keywords


def normalize_author_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (list, tuple, set)):
        pieces = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(pieces) or None
    stripped = str(value).strip()
    return stripped or None


def first_url_from_metadata(metadata: dict[str, Any]) -> str | None:
    for field_name in ("url", "source", "source_url"):
        for item in iter_strings(metadata.get(field_name)):
            candidate = item.strip()
            if not candidate:
                continue
            match = URL_RE.search(candidate)
            if match:
                return match.group(0)
            parsed = urlparse(candidate)
            if parsed.scheme and parsed.netloc:
                return candidate
            if "." in candidate and " " not in candidate:
                reparsed = urlparse(f"https://{candidate}")
                if reparsed.netloc:
                    return f"https://{candidate}"
    return None


def author_is_poor(author_value: str | None, min_length: int) -> bool:
    if author_value is None:
        return True
    return len(author_value.strip()) <= min_length


def domain_to_author(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.strip().lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def metadata_core_shared_keywords(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in iter_strings(metadata.get(CORE_SHARED_KEYWORDS_FIELD)):
        normalized = normalize_keyword(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def core_shared_keywords_changed(note: ParsedNote) -> bool:
    if not isinstance(note.metadata, dict):
        return False
    return metadata_core_shared_keywords(note.metadata) != note.core_shared_keywords


def author_field_normalization_needed(note: ParsedNote) -> bool:
    return isinstance(note.metadata, dict) and "authur" in note.metadata


def build_indexes(notes: list[ParsedNote]) -> tuple[dict[str, list[ParsedNote]], dict[str, list[ParsedNote]]]:
    keyword_index: dict[str, list[ParsedNote]] = defaultdict(list)
    author_index: dict[str, list[ParsedNote]] = defaultdict(list)
    for note in notes:
        if note.parse_error:
            continue
        if not note.core_shared_keywords and not note.author_values:
            continue
        for keyword in note.core_shared_keywords:
            keyword_index[keyword].append(note)
        for author_value in note.author_values:
            author_key = normalize_author_key(author_value)
            if author_key:
                author_index[author_key].append(note)
    return keyword_index, author_index


def score_candidates(
    note: ParsedNote,
    keyword_index: dict[str, list[ParsedNote]],
    author_index: dict[str, list[ParsedNote]],
) -> list[BacklinkTarget]:
    shared_keywords_by_path: dict[Path, set[str]] = defaultdict(set)
    shared_authors_by_path: dict[Path, set[str]] = defaultdict(set)
    candidates_by_path: dict[Path, ParsedNote] = {}

    for keyword in note.core_shared_keywords:
        matches = keyword_index.get(keyword, [])
        if len(matches) > CORE_SHARED_KEYWORD_MAX_MATCHES:
            continue
        for other in matches:
            if other.path == note.path:
                continue
            candidates_by_path[other.path] = other
            shared_keywords_by_path[other.path].add(keyword)

    for author_value in note.author_values:
        author_key = normalize_author_key(author_value)
        if not author_key:
            continue
        for other in author_index.get(author_key, []):
            if other.path == note.path:
                continue
            candidates_by_path[other.path] = other
            shared_authors_by_path[other.path].add(author_value)

    ranked: list[BacklinkTarget] = []
    for path, candidate in candidates_by_path.items():
        ranked.append(
            BacklinkTarget(
                note=candidate,
                shared_core_keywords=sorted(shared_keywords_by_path.get(path, set())),
                shared_authors=sorted(shared_authors_by_path.get(path, set())),
            )
        )
    ranked = sorted(
        ranked,
        key=lambda item: (-item.score, item.note.wikilink_target.casefold()),
    )
    return ranked


def already_linked(note: ParsedNote, candidate: BacklinkTarget) -> bool:
    for key in candidate.note.link_keys:
        if key in note.existing_links:
            return True
    return False


def propose_changes(
    notes: list[ParsedNote],
    keyword_index: dict[str, list[ParsedNote]],
    author_index: dict[str, list[ParsedNote]],
    author_min_length: int,
    max_backlinks: int | None,
    ref_authors: dict[str, str] | None = None,
) -> list[NoteProposal]:
    proposals: list[NoteProposal] = []
    ref = ref_authors or {}
    for note in notes:
        if note.parse_error:
            continue
        author_candidate = None
        if author_is_poor(note.author_value, author_min_length):
            author_candidate = match_author_from_ref(note, ref)
            if not author_candidate:
                author_candidate = domain_to_author(note.source_url)
        backlink_targets = [
            candidate
            for candidate in score_candidates(note, keyword_index, author_index)
            if not already_linked(note, candidate)
        ]
        if max_backlinks is not None:
            backlink_targets = backlink_targets[:max_backlinks]
        proposal = NoteProposal(
            note=note,
            author_candidate=author_candidate,
            backlink_targets=backlink_targets,
            core_shared_keywords_changed=core_shared_keywords_changed(note),
            author_field_normalization_needed=author_field_normalization_needed(note),
            needs_block_consolidation=body_needs_consolidation(note.body),
        )
        if proposal.has_changes:
            proposals.append(proposal)
    return proposals


def build_consolidation_proposals(notes: list[ParsedNote]) -> list[NoteProposal]:
    """Consolidation-only proposals: merge stacked shared blocks, change nothing else."""
    proposals: list[NoteProposal] = []
    for note in notes:
        if note.parse_error:
            continue
        if not body_needs_consolidation(note.body):
            continue
        proposals.append(
            NoteProposal(
                note=note,
                author_candidate=None,
                backlink_targets=[],
                needs_block_consolidation=True,
                consolidation_only=True,
            )
        )
    return proposals


def filter_proposals_by_target_glob(
    proposals: list[NoteProposal],
    target_path_globs: list[str],
) -> list[NoteProposal]:
    if not target_path_globs:
        return proposals
    return [
        proposal
        for proposal in proposals
        if path_matches_globs(proposal.note.relative_path, target_path_globs)
    ]


def limit_items(items: list[Any], limit: int) -> tuple[list[Any], int]:
    if limit <= 0 or len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def format_link_preview(targets: list[BacklinkTarget], limit: int) -> str:
    visible_targets, hidden_count = limit_items(targets, limit)
    links = ", ".join(target.note.wikilink for target in visible_targets)
    if hidden_count:
        return f"{links}, ... (+{hidden_count} more)"
    return links


def _parse_shared_block_line(line: str) -> tuple[str, str] | None:
    """Classify a body line as a shared-block line.

    Returns (kind, remainder) where remainder holds everything after the label,
    or None when the line is not a shared block. Tolerates label drift (emoji
    variation selector, missing/misplaced bold markers, spacing, letter case),
    but requires the remainder to be empty or start with a wikilink so prose
    that merely mentions "shared keywords" is never treated as a block.
    """
    match = SHARED_BLOCK_LINE_RE.match(line)
    if match is None:
        return None
    remainder = match.group(2).strip()
    if remainder and not remainder.startswith("[["):
        return None
    return match.group(1).lower(), remainder


def _shared_block_kind(line: str) -> str | None:
    parsed = _parse_shared_block_line(line)
    return parsed[0] if parsed else None


def shared_block_line_count(body: str, kind: str) -> int:
    """Number of body lines that are shared-block entries for the given kind."""
    return sum(1 for line in body.splitlines() if _shared_block_kind(line) == kind)


def shared_block_links(body: str, kind: str) -> list[str]:
    """Wikilink targets found on every shared-block line for kind, in order.

    Falls back to a lenient bracket matcher when WIKILINK_RE cannot parse a
    line's links (e.g. targets whose own name starts with "[", serializing as
    [[[name]]]), so those blocks are still merged instead of silently skipped.
    """
    links: list[str] = []
    for line in body.splitlines():
        parsed = _parse_shared_block_line(line)
        if parsed is None or parsed[0] != kind:
            continue
        matches = list(WIKILINK_RE.finditer(parsed[1]))
        if matches:
            links.extend(match.group(1) for match in matches)
        else:
            links.extend(match.group(1) for match in FALLBACK_BLOCK_LINK_RE.finditer(parsed[1]))
    return links


def body_needs_consolidation(body: str) -> bool:
    """True when the body has stacked duplicate shared-block lines that should be merged."""
    return (
        shared_block_line_count(body, SHARED_BLOCK_KIND_KEYWORDS) >= 2
        or shared_block_line_count(body, SHARED_BLOCK_KIND_AUTHORS) >= 2
    )


def serialize_frontmatter(metadata: Any, newline: str) -> str:
    buffer = io.StringIO()
    YAML_PARSER.dump(metadata, buffer)
    dumped = buffer.getvalue().rstrip("\n")
    if newline == "\r\n":
        dumped = dumped.replace("\n", "\r\n")
    return dumped


def _bare_wikilink_target(link: str) -> str:
    """Strip [[...]] wrapping so existing and new links compare on equal footing."""
    text = link.strip()
    match = re.match(r"^\[\[(.+)\]\]$", text)
    return match.group(1).strip() if match else text


def strip_shared_blocks(body: str, kind: str, newline: str) -> str:
    """Remove every shared-block line for kind plus its immediately preceding '---' separator."""
    kept: list[str] = []
    for line in body.splitlines():
        if _shared_block_kind(line) == kind:
            if kept and kept[-1].strip() == "---":
                kept.pop()
            continue
        kept.append(line)
    return newline.join(kept)


def merge_shared_block(
    body: str,
    kind: str,
    new_links: list[str],
    newline: str,
    self_keys: set[str] | None = None,
) -> str:
    """Collapse every shared-block line for kind into one, unioned with new_links.

    Idempotent: a body that already has a single up-to-date block is returned
    unchanged on a second pass. When there are no links at all the block is
    removed entirely instead of being re-added. Links that point back at the
    note itself (self_keys) are dropped, and deduplication compares normalized
    link keys so "[[Note]]" and "Note" are recognized as the same target.
    Returns the body untouched when there is no existing block of this kind
    and nothing new to add.
    """
    existing_links = shared_block_links(body, kind)
    if shared_block_line_count(body, kind) == 0 and not new_links:
        return body
    candidates = [_bare_wikilink_target(link) for link in existing_links]
    candidates += [_bare_wikilink_target(link) for link in new_links]
    merged_links: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = normalize_link_key(candidate)
        if key in seen or (self_keys and key in self_keys):
            continue
        seen.add(key)
        merged_links.append(candidate)
    cleaned = strip_shared_blocks(body, kind, newline).rstrip("\r\n")
    if not merged_links:
        return (cleaned + newline) if cleaned else ""
    label = SHARED_BLOCK_KIND_LABELS[kind]
    joined_links = ", ".join(f"[[{link}]]" for link in merged_links)
    block = f"---{newline}{label} {joined_links}{newline}"
    if not cleaned:
        return block
    return f"{cleaned}{newline}{newline}{block}"


def append_unique_items(existing_items: list[str], new_items: list[str]) -> list[str]:
    result = list(existing_items)
    seen = {item.strip().casefold() for item in existing_items if item.strip()}
    for item in new_items:
        stripped = item.strip()
        if not stripped:
            continue
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(stripped)
    return result


def existing_author_items(metadata: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for field_name in ("author", "authur"):
        items = append_unique_items(items, [str(item).strip() for item in iter_strings(metadata.get(field_name))])
    return items


def update_author_metadata(metadata: dict[str, Any], proposal: NoteProposal) -> None:
    existing_items = existing_author_items(metadata)
    backlink_items = [target.note.wikilink for target in proposal.author_backlink_targets]
    combined_items = append_unique_items(
        existing_items,
        ([proposal.author_candidate] if proposal.author_candidate else []) + backlink_items,
    )

    if "authur" in metadata:
        del metadata["authur"]

    if not combined_items:
        if "author" in metadata:
            del metadata["author"]
        return

    prefer_list = isinstance(metadata.get("author"), (list, tuple, set)) or len(combined_items) > 1
    metadata["author"] = combined_items if prefer_list else combined_items[0]


def update_core_shared_keywords_metadata(metadata: dict[str, Any], core_shared_keywords: list[str]) -> None:
    if core_shared_keywords:
        metadata[CORE_SHARED_KEYWORDS_FIELD] = list(core_shared_keywords)
    elif CORE_SHARED_KEYWORDS_FIELD in metadata:
        del metadata[CORE_SHARED_KEYWORDS_FIELD]


def render_consolidation_text(proposal: NoteProposal) -> str:
    """Consolidation-only render: verbatim frontmatter + merged body.

    The frontmatter text is written back byte-for-byte (no ruamel round-trip)
    so a vault-wide duplicate-block cleanup only touches the shared blocks.
    """
    note = proposal.note
    newline = note.newline
    body = merge_shared_block(note.body, SHARED_BLOCK_KIND_KEYWORDS, [], newline, self_keys=note.link_keys)
    body = merge_shared_block(body, SHARED_BLOCK_KIND_AUTHORS, [], newline, self_keys=note.link_keys)
    if note.frontmatter_text is None:
        return body
    return f"---{newline}{note.frontmatter_text}{newline}---{newline}{body.lstrip(chr(13) + chr(10))}"


def render_updated_text(proposal: NoteProposal) -> str:
    note = proposal.note
    if proposal.consolidation_only:
        return render_consolidation_text(proposal)
    metadata = note.metadata
    if metadata is None:
        metadata = {}
        note.metadata = metadata
    if proposal.author_candidate or proposal.author_backlink_targets or proposal.author_field_normalization_needed:
        update_author_metadata(metadata, proposal)
    if proposal.core_shared_keywords_changed:
        update_core_shared_keywords_metadata(metadata, note.core_shared_keywords)
    body = note.body
    newline = note.newline
    # Idempotent shared-block handling: merge any existing block(s) with the new
    # links so repeated runs never stack duplicate 🔗 Shared Keywords/Authors blocks.
    if proposal.keyword_backlink_targets or proposal.needs_block_consolidation:
        body = merge_shared_block(
            body,
            SHARED_BLOCK_KIND_KEYWORDS,
            [target.note.wikilink for target in proposal.keyword_backlink_targets],
            newline,
            self_keys=note.link_keys,
        )
    if proposal.body_author_backlink_targets or proposal.needs_block_consolidation:
        body = merge_shared_block(
            body,
            SHARED_BLOCK_KIND_AUTHORS,
            [target.note.wikilink for target in proposal.body_author_backlink_targets],
            newline,
            self_keys=note.link_keys,
        )
    frontmatter = serialize_frontmatter(metadata, newline)
    return f"---{newline}{frontmatter}{newline}---{newline}{body.lstrip(chr(13) + chr(10))}"


def print_summary(notes: list[ParsedNote], proposals: list[NoteProposal], preview_error_limit: int) -> None:
    parse_errors = [note for note in notes if note.parse_error]
    author_only = sum(1 for proposal in proposals if proposal.author_candidate and not proposal.backlink_targets)
    backlinks_only = sum(1 for proposal in proposals if proposal.backlink_targets and not proposal.author_candidate)
    combined = sum(1 for proposal in proposals if proposal.author_candidate and proposal.backlink_targets)
    print(f"Scanned markdown notes: {len(notes)}")
    print(f"Frontmatter parse errors: {len(parse_errors)}")
    print(f"Candidate notes with changes: {len(proposals)}")
    print(f"  - author only: {author_only}")
    print(f"  - backlinks only: {backlinks_only}")
    print(f"  - author + backlinks: {combined}")
    if parse_errors:
        print("\nParse errors:")
        visible_errors, hidden_count = limit_items(parse_errors, preview_error_limit)
        for note in visible_errors:
            print(f"  - {note.relative_path.as_posix()}: {note.parse_error}")
        if hidden_count:
            print(f"  ... and {hidden_count} more")


def preview_proposals(proposals: list[NoteProposal], preview_link_limit: int) -> None:
    if not proposals:
        print("No orphan-note repairs were proposed.")
        return
    print("\nProposed changes:")
    for index, proposal in enumerate(proposals, start=1):
        note = proposal.note
        print(f"\n[{index}] {note.relative_path.as_posix()}")
        if proposal.author_candidate:
            current_author = note.author_value or "<missing>"
            print(f"  author: {current_author} -> {proposal.author_candidate}")
        if proposal.core_shared_keywords_changed:
            print(f"  {CORE_SHARED_KEYWORDS_FIELD}: {', '.join(note.core_shared_keywords) or '<empty>'}")
        if proposal.backlink_targets:
            print(f"  backlinks: {format_link_preview(proposal.backlink_targets, preview_link_limit)}")
        if proposal.needs_block_consolidation:
            print("  shared blocks: merge duplicates into one")


def prompt_choice(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return "q"


def apply_proposals(proposals: list[NoteProposal], mode: str, preview_link_limit: int) -> dict[str, Any]:
    applied = 0
    skipped = 0
    written_files: list[str] = []
    apply_rest = mode == "apply"

    for proposal in proposals:
        if mode == "interactive" and not apply_rest:
            note = proposal.note
            print(f"\nReview: {note.relative_path.as_posix()}")
            if proposal.author_candidate:
                print(f"  author -> {proposal.author_candidate}")
            if proposal.core_shared_keywords_changed:
                print(f"  {CORE_SHARED_KEYWORDS_FIELD} -> {', '.join(note.core_shared_keywords) or '<empty>'}")
            if proposal.backlink_targets:
                print("  backlinks -> " + format_link_preview(proposal.backlink_targets, preview_link_limit))
            if proposal.needs_block_consolidation:
                print("  shared blocks -> merge duplicates into one")
            choice = prompt_choice("Apply this change? [y]es/[n]o/[a]ll/[q]uit: ")
            if choice == "a":
                apply_rest = True
            elif choice == "q":
                skipped += 1
                break
            elif choice not in {"y", "yes"}:
                skipped += 1
                continue

        updated = render_updated_text(proposal)
        proposal.note.path.write_text(updated, encoding="utf-8")
        applied += 1
        written_files.append(proposal.note.relative_path.as_posix())

    return {
        "applied": applied,
        "skipped": skipped + max(0, len(proposals) - applied - skipped),
        "written_files": written_files,
    }


def iter_note_paths(vault_root: Path, args: argparse.Namespace) -> list[Path]:
    excluded_dirs = DEFAULT_EXCLUDED_DIRS | set(args.exclude_dir)
    include_patterns = build_include_patterns(vault_root)
    paths: list[Path] = []
    for path in sorted(vault_root.rglob("*.md")):
        relative_path = path.relative_to(vault_root)
        if should_skip_path(relative_path, excluded_dirs, args.path_glob, include_patterns):
            continue
        paths.append(path)
        if args.limit is not None and len(paths) >= args.limit:
            break
    return paths


def collect_notes(vault_root: Path, args: argparse.Namespace) -> list[ParsedNote]:
    notes: list[ParsedNote] = []
    for path in iter_note_paths(vault_root, args):
        relative_path = path.relative_to(vault_root)
        try:
            note = parse_note(path, vault_root)
        except UnicodeDecodeError as exc:
            note = ParsedNote(
                path=path,
                relative_path=relative_path,
                newline="\n",
                raw_text="",
                body="",
                frontmatter_text=None,
                metadata=None,
                parse_error=f"Unicode decode error: {exc}",
            )
        except Exception as exc:
            note = ParsedNote(
                path=path,
                relative_path=relative_path,
                newline="\n",
                raw_text="",
                body="",
                frontmatter_text=None,
                metadata=None,
                parse_error=f"Unexpected read error: {exc}",
            )
        notes.append(note)
    return notes


def collect_notes_for_target_scope(vault_root: Path, args: argparse.Namespace) -> tuple[list[ParsedNote], list[ParsedNote]]:
    notes = collect_notes(vault_root, args)
    target_notes = [
        note for note in notes if path_matches_globs(note.relative_path, args.target_path_glob)
    ]
    return notes, target_notes


def write_report(path: Path, notes: list[ParsedNote], proposals: list[NoteProposal], apply_result: dict[str, Any]) -> None:
    report = {
        "scanned_notes": len(notes),
        "parse_errors": [
            {"path": note.relative_path.as_posix(), "error": note.parse_error}
            for note in notes
            if note.parse_error
        ],
        "proposals": [
            {
                "path": proposal.note.relative_path.as_posix(),
                "author_candidate": proposal.author_candidate,
                "core_shared_keywords": proposal.note.core_shared_keywords,
                "backlink_targets": [
                    {
                        "path": target.note.wikilink_target,
                        "shared_core_keywords": target.shared_core_keywords,
                        "shared_authors": target.shared_authors,
                    }
                    for target in proposal.backlink_targets
                ],
            }
            for proposal in proposals
        ],
        "apply_result": apply_result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.yes:
        args.mode = "apply"

    vault_root = Path(args.vault).expanduser().resolve()
    if not vault_root.exists() or not vault_root.is_dir():
        print(f"Vault path does not exist or is not a directory: {vault_root}", file=sys.stderr)
        return 2

    ref_authors = load_author_refs(args.author_ref, vault_root) if args.author_ref else {}

    if args.consolidate_only:
        notes = collect_notes(vault_root, args)
        proposals = build_consolidation_proposals(notes)
    elif args.target_path_glob:
        notes, target_notes = collect_notes_for_target_scope(vault_root, args)
        keyword_index, author_index = build_indexes(notes)
        proposals = propose_changes(
            target_notes,
            keyword_index,
            author_index,
            author_min_length=args.author_min_length,
            max_backlinks=args.max_backlinks,
            ref_authors=ref_authors,
        )
    else:
        notes = collect_notes(vault_root, args)
        keyword_index, author_index = build_indexes(notes)
        proposals = propose_changes(
            notes,
            keyword_index,
            author_index,
            author_min_length=args.author_min_length,
            max_backlinks=args.max_backlinks,
            ref_authors=ref_authors,
        )
    proposals = filter_proposals_by_target_glob(proposals, args.target_path_glob)

    print_summary(notes, proposals, args.preview_error_limit)
    preview_proposals(proposals, args.preview_link_limit)

    apply_result = {"applied": 0, "skipped": len(proposals), "written_files": []}
    if args.mode in {"interactive", "apply"} and proposals:
        apply_result = apply_proposals(proposals, args.mode, args.preview_link_limit)
        print("\nApply summary:")
        print(f"  applied: {apply_result['applied']}")
        print(f"  skipped: {apply_result['skipped']}")
    elif args.mode == "preview":
        print("\nPreview mode only: no files were modified.")

    if args.report_json:
        write_report(Path(args.report_json), notes, proposals, apply_result)
        print(f"JSON report written to: {args.report_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
