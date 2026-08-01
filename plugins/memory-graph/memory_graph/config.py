"""Centralized resolution of the memory directory and index DB path.

Every entrypoint (CLI subcommands, MCP server tools) resolves through this
module so the auto-detection algorithm exists exactly once — no duplicated
detection logic between cli.py / server.py / store.py.

The memory directory is expected to be an **Obsidian vault** (a directory
containing `.obsidian/`). Writes go through the `obsidian` CLI; this package
only ever reads. The legacy `~/.claude/projects/<slug>/memory` layout is still
auto-detected as a last resort so existing installs keep working until they
migrate (see the `memory-graph:memory-vault-setup` skill).
"""

from __future__ import annotations

import os
from pathlib import Path


def project_slug(project_dir: str) -> str:
    """Claude Code's project slug: absolute path with every '/' -> '-'.

    e.g. /Users/lclpedro/projects/LoopMed -> -Users-lclpedro-projects-LoopMed
    """
    return project_dir.replace("/", "-")


def _current_project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _claude_project_root(project_dir: str) -> Path:
    slug = project_slug(os.path.abspath(project_dir))
    return Path.home() / ".claude" / "projects" / slug


def is_vault(path: Path) -> bool:
    """An Obsidian vault is any directory holding a `.obsidian/` config dir."""
    return path.is_dir() and (path / ".obsidian").is_dir()


def find_vault(project_dir: str) -> Path | None:
    """Locate this project's Obsidian vault.

    Checks the project root itself, then each immediate subdirectory (the
    usual layout is `<project>/<Name>Memory/`). Hidden and dependency
    directories are skipped. When several vaults exist, the one whose name
    contains "memory" wins; otherwise the first in sorted order, so the result
    is deterministic instead of filesystem-order dependent.
    """
    root = Path(os.path.abspath(project_dir))
    if not root.is_dir():
        return None
    if is_vault(root):
        return root

    skip = {"node_modules", "venv", ".venv", "vendor", "dist", "build", "target"}
    found = sorted(
        (c for c in root.iterdir()
         if not c.name.startswith(".") and c.name not in skip and is_vault(c)),
        key=lambda p: p.name,
    )
    if not found:
        return None
    for c in found:
        if "memory" in c.name.lower():
            return c
    return found[0]


def resolve_memory_dir(explicit: str | None = None, *, required: bool = True) -> str | None:
    """Resolve the memory directory.

    Resolution order:
      1. `explicit` (e.g. a CLI `--dir` value) — must exist.
      2. `$MEMORY_GRAPH_DIR` — must exist.
      3. The project's **Obsidian vault** — a directory containing
         `.obsidian/`, either the project root or an immediate subdirectory
         (typically `<project>/<Name>Memory/`).
      4. Legacy fallback: `~/.claude/projects/<slug>/memory`, where `<slug>`
         is the absolute project path with every `/` replaced by `-`. Kept so
         installs that predate the vault layout keep working; run the
         `memory-graph:memory-vault-setup` skill to migrate.

    An `explicit` value or a set-but-missing `$MEMORY_GRAPH_DIR` always
    raises `FileNotFoundError` (the caller asked for that exact path).
    Pure auto-detection (step 3) only raises when `required=True`; with
    `required=False` it returns `None` so callers can treat "couldn't
    auto-detect" as a soft no-op (e.g. skipping a lazy reindex) instead of
    a hard failure.
    """
    if explicit:
        if Path(explicit).is_dir():
            return explicit
        raise FileNotFoundError(f"memory directory not found: {explicit}")

    env = os.environ.get("MEMORY_GRAPH_DIR")
    if env:
        if Path(env).is_dir():
            return env
        raise FileNotFoundError(
            f"MEMORY_GRAPH_DIR is set to {env!r} but that directory does not exist. "
            "Point it at the folder containing your memory .md files."
        )

    project_dir = _current_project_dir()

    vault = find_vault(project_dir)
    if vault is not None:
        return str(vault)

    legacy = _claude_project_root(project_dir) / "memory"
    if legacy.is_dir():
        return str(legacy)

    if not required:
        return None

    raise FileNotFoundError(
        "Could not auto-detect a memory directory.\n"
        f"  No Obsidian vault (a directory containing .obsidian/) found in: {project_dir}\n"
        f"  No legacy memory directory at: {legacy}\n"
        "Run the `memory-graph:memory-vault-setup` skill to create a vault, or point\n"
        "MEMORY_GRAPH_DIR at an existing one:\n"
        "  export MEMORY_GRAPH_DIR=/path/to/YourVault"
    )


def resolve_db_path(explicit: str | None = None) -> str:
    """Resolve the SQLite index path.

    Resolution order: `explicit` -> `$MEMORY_GRAPH_DB` -> a stable
    per-project path *outside* the memory directory so the index never
    pollutes it: `~/.claude/projects/<slug>/.memory-graph/index.db`.
    """
    if explicit:
        return explicit

    env = os.environ.get("MEMORY_GRAPH_DB")
    if env:
        return env

    return str(_claude_project_root(_current_project_dir()) / ".memory-graph" / "index.db")
