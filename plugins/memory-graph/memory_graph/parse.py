"""Parse memory markdown files: YAML frontmatter + [[links]] extraction.

Markdown is the source of truth. This module only reads files; it never
writes them.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from .model import MemoryDoc

# Matches `[[slug]]`, `[[slug|alias]]`, `[[slug#section]]` — only the slug
# (first segment) is captured.
LINK_RE = re.compile(r"\[\[([^\]|#]+)")

# Frontmatter block: `---\n<yaml>\n---\n<body>`
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?(.*)$", re.DOTALL)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_links(body: str) -> list[str]:
    """Extract unique `[[slug]]` link targets from a memory body, in order."""
    seen: list[str] = []
    for raw in LINK_RE.findall(body):
        slug = raw.strip()
        if slug and slug not in seen:
            seen.append(slug)
    return seen


def parse_file(path: Path) -> MemoryDoc | None:
    """Parse a single `.md` file into a MemoryDoc.

    Returns None for files without a YAML frontmatter block (e.g. an index
    file like MEMORY.md) — those are not memories, just navigation aids.
    """
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return None

    fm_text, body = match.group(1), match.group(2)
    try:
        frontmatter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        frontmatter = {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}

    name = str(frontmatter.get("name") or path.stem).strip()
    description = str(frontmatter.get("description") or "").strip()

    metadata = frontmatter.get("metadata")
    doc_type = ""
    if isinstance(metadata, dict):
        doc_type = str(metadata.get("type") or "").strip()

    body = body.strip()
    return MemoryDoc(
        name=name,
        description=description,
        type=doc_type,
        body=body,
        links=extract_links(body),
        path=str(path),
        mtime=path.stat().st_mtime,
        hash=_hash(raw),
    )


def scan_dir(directory: str) -> list[MemoryDoc]:
    """Parse every `.md` file in `directory` (non-recursive) into MemoryDocs.

    Files without frontmatter (e.g. an index like MEMORY.md) are skipped.
    """
    docs: list[MemoryDoc] = []
    for md_path in sorted(Path(directory).glob("*.md")):
        doc = parse_file(md_path)
        if doc is not None:
            docs.append(doc)
    return docs
