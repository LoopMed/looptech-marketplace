"""Data model for a single memory markdown file."""

from dataclasses import dataclass, field


@dataclass
class MemoryDoc:
    """One parsed memory file.

    `name` is the frontmatter `name:` value — the canonical ID other memories
    reference via `[[name]]` links. `links` are the raw `[[slug]]` targets
    found in the body (not yet resolved against the store).
    """

    name: str
    description: str
    type: str
    body: str
    links: list[str] = field(default_factory=list)
    path: str = ""
    mtime: float = 0.0
    hash: str = ""
