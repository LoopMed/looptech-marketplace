"""MCP server exposing the memory graph as tools (FastMCP, stdio transport).

Everything here runs 100% locally: the SQLite index and the fastembed ONNX
model both live on disk, no network call is made while serving a request.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import resolve_db_path, resolve_memory_dir
from .embed import Embedder
from .index import ensure_fresh
from .index import reindex as run_reindex
from .search import get as run_get
from .search import neighbors as run_neighbors
from .search import search as run_search
from .store import Store

mcp = FastMCP("memory-graph")

_embedder: Embedder | None = None


def _db_path() -> str:
    return resolve_db_path()


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


@mcp.tool()
def memory_search(query: str, k: int = 5) -> list[dict]:
    """Semantic search over indexed memories.

    Ranks memories by embedding (vector) similarity to `query`, NOT keyword
    matching — it will surface conceptually related memories even when they
    don't share exact words with the query. Returns up to `k` results, each
    with name, similarity score, description, type and file path.

    The index is lazily brought up to date first (only files whose content
    changed since the last query get re-embedded), so results always
    reflect the current memory files with no manual reindex needed.
    """
    store = Store(_db_path())
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        return run_search(store, _get_embedder(), query, k)
    finally:
        store.close()


@mcp.tool()
def memory_get(name: str) -> dict | None:
    """Fetch a single memory by its frontmatter `name` (or filename).

    Lazily reindexes first (see `memory_search`), so edits to the source
    file are reflected without a manual reindex.
    """
    store = Store(_db_path())
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        return run_get(store, name)
    finally:
        store.close()


@mcp.tool()
def memory_neighbors(name: str, depth: int = 1) -> dict:
    """Follow the `[[link]]` graph out from a memory.

    Returns the memories directly (or, at higher `depth`, transitively)
    linked to/from `name` via `[[wikilink]]` references in the markdown
    body — the graph-traversal counterpart to `memory_search`'s semantic
    recall. Lazily reindexes first (see `memory_search`).
    """
    store = Store(_db_path())
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        return run_neighbors(store, name, depth)
    finally:
        store.close()


@mcp.tool()
def memory_reindex(directory: str | None = None) -> dict:
    """Re-scan the memory directory and update the local index.

    Incremental: only memories whose content changed since the last index
    are re-embedded. `directory` is optional — it defaults to
    `MEMORY_GRAPH_DIR` and, failing that, is auto-detected from the current
    Claude Code project (`~/.claude/projects/<slug>/memory`). This tool is
    only needed for an explicit/manual refresh; `memory_search`,
    `memory_get` and `memory_neighbors` already reindex lazily on their own.
    """
    resolved = resolve_memory_dir(directory, required=True)
    return run_reindex(resolved, _db_path())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
