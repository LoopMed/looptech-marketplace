"""Centralized resolution of the memory directory and index DB path.

Every entrypoint (CLI subcommands, MCP server tools) resolves through this
module so the auto-detection algorithm exists exactly once — no duplicated
detection logic between cli.py / server.py / store.py.

The memory directory is expected to be an **Obsidian vault** (a directory
containing `.obsidian/`). Writes go through the `obsidian` CLI; this package
only ever reads. The legacy `~/.claude/projects/<slug>/memory` layout is still
auto-detected as a last resort so existing installs keep working until they
migrate (see the `memory-graph:memory-vault-setup` skill). The SQLite index
defaults to `~/.looptech/memory-graph/<slug>/index.db` so Codex and Cursor
do not depend on a Claude-only path.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


_MEMORY_BLOCK_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)memory:[ \t]*(?:#.*)?\n"
    r"(?P<body>(?:(?:(?P=indent)[ \t]+[^\n]*|[ \t]*)\n)*)"
)


def project_slug(project_dir: str) -> str:
    """Stable project slug: absolute path with every '/' -> '-'.

    e.g. /Users/lclpedro/projects/LoopMed -> -Users-lclpedro-projects-LoopMed
    """
    return project_dir.replace("/", "-")


def _usable_env(name: str) -> str | None:
    """Return an env value only if the host actually set it.

    Empty strings and leftover `${PLACEHOLDER}` expansions (hosts that pass
    the literal token when the variable is unset) are treated as unset so
    auto-detection still runs.
    """
    value = os.environ.get(name)
    if not value:
        return None
    if value.startswith("${") and value.endswith("}"):
        return None
    return value


def _current_project_dir() -> str:
    return (
        _usable_env("CLAUDE_PROJECT_DIR")
        or _usable_env("CURSOR_PROJECT_DIR")
        or os.getcwd()
    )


def _claude_project_root(project_dir: str) -> Path:
    slug = project_slug(os.path.abspath(project_dir))
    return Path.home() / ".claude" / "projects" / slug


def _looptech_index_path(project_dir: str) -> Path:
    slug = project_slug(os.path.abspath(project_dir))
    return Path.home() / ".looptech" / "memory-graph" / slug / "index.db"


def is_vault(path: Path) -> bool:
    """An Obsidian vault is any directory holding a `.obsidian/` config dir."""
    return path.is_dir() and (path / ".obsidian").is_dir()


def find_vault(project_dir: str) -> Path | None:
    """Locate an Obsidian vault in `project_dir` itself or an immediate child.

    Hidden and dependency directories are skipped. When several vaults exist,
    the one whose name contains "memory" wins; otherwise the first in sorted
    order, so the result is deterministic instead of filesystem-order dependent.
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


def _parse_memory_path(text: str) -> str | None:
    """Extract `memory.path` from a CLAUDE.md / AGENTS.md body.

    Accepts a YAML `memory:` mapping (fenced or raw) and strips inline
    comments via the YAML loader. First block that yields a non-empty
    `path` wins. Product-agnostic: no hardcoded vault names.
    """
    for match in _MEMORY_BLOCK_RE.finditer(text):
        snippet = match.group(0)
        try:
            data = yaml.safe_load(snippet)
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        memory = data.get("memory")
        if not isinstance(memory, dict):
            continue
        path = memory.get("path")
        if isinstance(path, str) and path.strip():
            return path.strip()
    return None


def _declared_memory_dir(level: Path) -> Path | None:
    """Resolve `memory.path` from CLAUDE.md / AGENTS.md at `level`.

    The path is relative to the file's directory (not the process cwd).
    An existing directory is enough; a `.obsidian/` vault is preferred
    but not required.
    """
    for name in ("CLAUDE.md", "AGENTS.md"):
        source = level / name
        if not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.endswith("\n"):
            text += "\n"
        raw = _parse_memory_path(text)
        if not raw:
            continue
        resolved = (source.parent / raw).resolve()
        if resolved.is_dir():
            return resolved
    return None


def _is_under_or_equal(path: Path, home: Path) -> bool:
    try:
        path.resolve().relative_to(home)
        return True
    except ValueError:
        return False


def _ancestor_chain(project_dir: str) -> list[Path]:
    """Ancestors from `project_dir` up to `$HOME` inclusive, never above HOME.

    If the project lives outside HOME, only the starting directory is
    returned so we do not walk to filesystem root.
    """
    start = Path(os.path.abspath(project_dir))
    home = Path.home().resolve()
    chain: list[Path] = []
    current = start
    while True:
        chain.append(current)
        if current.resolve() == home:
            break
        parent = current.parent
        if parent == current:
            break
        if not _is_under_or_equal(start, home):
            break
        if not (_is_under_or_equal(parent, home) or parent.resolve() == home):
            break
        current = parent
    return chain


def _legacy_has_notes(legacy: Path) -> bool:
    """Legacy harness dirs are created empty; only count those with a .md."""
    if not legacy.is_dir():
        return False
    return any(p.is_file() and p.suffix == ".md" for p in legacy.rglob("*.md"))


def resolve_memory_dir(explicit: str | None = None, *, required: bool = True) -> str | None:
    """Resolve the memory directory.

    Resolution order:
      1. `explicit` (e.g. a CLI `--dir` value) — must exist.
      2. `$MEMORY_GRAPH_DIR` via `_usable_env` (empty and `${placeholder}`
         are ignored). A real value that is missing always raises.
      3. Walk ancestors from the project dir up to `$HOME` (inclusive):
         a. `memory.path` in `CLAUDE.md` / `AGENTS.md`, resolved relative
            to the file's directory. An existing dir is enough.
         b. `find_vault(level)` — the level itself or an immediate child
            containing `.obsidian/`.
         First hit wins (closest to the project).
      4. Legacy `~/.claude/projects/<slug>/memory` only if it contains at
         least one `.md`. An empty harness directory does not count.
      5. If `required=True` and nothing resolved, raise pointing at
         `MEMORY_GRAPH_DIR` / the setup skill. If `required=False`, `None`.
    """
    if explicit:
        if Path(explicit).is_dir():
            return explicit
        raise FileNotFoundError(f"memory directory not found: {explicit}")

    env = _usable_env("MEMORY_GRAPH_DIR")
    if env:
        if Path(env).is_dir():
            return env
        raise FileNotFoundError(
            f"MEMORY_GRAPH_DIR is set to {env!r} but that directory does not exist. "
            "Point it at the folder containing your memory .md files."
        )

    project_dir = _current_project_dir()

    for level in _ancestor_chain(project_dir):
        declared = _declared_memory_dir(level)
        if declared is not None:
            return str(declared)
        vault = find_vault(str(level))
        if vault is not None:
            return str(vault)

    legacy = _claude_project_root(project_dir) / "memory"
    if _legacy_has_notes(legacy):
        return str(legacy)

    if not required:
        return None

    raise FileNotFoundError(
        "Could not auto-detect a memory directory.\n"
        f"  No Obsidian vault (a directory containing .obsidian/) found in: {project_dir}\n"
        f"  No memory.path in CLAUDE.md/AGENTS.md along the ancestor walk to $HOME\n"
        f"  No legacy memory directory with .md notes at: {legacy}\n"
        "Run the `memory-graph:memory-vault-setup` skill to create a vault, or point\n"
        "MEMORY_GRAPH_DIR at an existing one:\n"
        "  export MEMORY_GRAPH_DIR=/path/to/YourVault"
    )


def resolve_db_path(explicit: str | None = None) -> str:
    """Resolve the SQLite index path.

    Resolution order: `explicit` -> `$MEMORY_GRAPH_DB` -> an existing
    Claude-era index at `~/.claude/projects/<slug>/.memory-graph/index.db`
    (kept so upgraded installs do not re-embed) -> host-neutral
    `~/.looptech/memory-graph/<slug>/index.db`.
    """
    if explicit:
        return explicit

    env = _usable_env("MEMORY_GRAPH_DB")
    if env:
        return env

    project_dir = _current_project_dir()
    legacy = _claude_project_root(project_dir) / ".memory-graph" / "index.db"
    if legacy.is_file():
        return str(legacy)
    return str(_looptech_index_path(project_dir))
