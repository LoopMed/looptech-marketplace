"""Centralized resolution of the memory directory and index DB path.

Every entrypoint (CLI subcommands, MCP server tools) resolves through this
module so the auto-detection algorithm exists exactly once — no duplicated
slug logic between cli.py / server.py / store.py.
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


def resolve_memory_dir(explicit: str | None = None, *, required: bool = True) -> str | None:
    """Resolve the memory directory.

    Resolution order:
      1. `explicit` (e.g. a CLI `--dir` value) — must exist.
      2. `$MEMORY_GRAPH_DIR` — must exist.
      3. Derived from `$CLAUDE_PROJECT_DIR` (else `cwd`) via
         `~/.claude/projects/<slug>/memory`, where `<slug>` is the absolute
         project path with every `/` replaced by `-`.

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

    candidate = _claude_project_root(_current_project_dir()) / "memory"
    if candidate.is_dir():
        return str(candidate)

    if not required:
        return None

    raise FileNotFoundError(
        "Could not auto-detect a memory directory.\n"
        f"  Looked for: {candidate}\n"
        "Set MEMORY_GRAPH_DIR to the folder containing your memory .md files, e.g.:\n"
        "  export MEMORY_GRAPH_DIR=/path/to/memory"
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
