"""MCP server exposing the memory graph as tools (FastMCP, stdio transport).

Everything here runs 100% locally: the SQLite index and the fastembed ONNX
model both live on disk, no network call is made while serving a request.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .embed import Embedder
from .index import reindex as run_reindex
from .search import get as run_get
from .search import neighbors as run_neighbors
from .search import search as run_search
from .store import Store, default_db_path

mcp = FastMCP("memory-graph")

_embedder: Embedder | None = None


def _db_path() -> str:
    return os.environ.get("MEMORY_GRAPH_DB", default_db_path())


def _dir_path() -> str | None:
    return os.environ.get("MEMORY_GRAPH_DIR")


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
    """
    store = Store(_db_path())
    try:
        return run_search(store, _get_embedder(), query, k)
    finally:
        store.close()


@mcp.tool()
def memory_get(name: str) -> dict | None:
    """Fetch a single memory by its frontmatter `name` (or filename)."""
    store = Store(_db_path())
    try:
        return run_get(store, name)
    finally:
        store.close()


@mcp.tool()
def memory_neighbors(name: str, depth: int = 1) -> dict:
    """Follow the `[[link]]` graph out from a memory.

    Returns the memories directly (or, at higher `depth`, transitively)
    linked to/from `name` via `[[wikilink]]` references in the markdown
    body — the graph-traversal counterpart to `memory_search`'s semantic
    recall.
    """
    store = Store(_db_path())
    try:
        return run_neighbors(store, name, depth)
    finally:
        store.close()


@mcp.tool()
def memory_reindex(directory: str | None = None) -> dict:
    """Re-scan the memory directory and update the local index.

    Incremental: only memories whose content changed since the last index
    are re-embedded. Requires `directory` (or the MEMORY_GRAPH_DIR env var)
    to point at the folder of memory markdown files.
    """
    directory = directory or _dir_path()
    if not directory:
        raise ValueError(
            "directory is required (pass it explicitly or set MEMORY_GRAPH_DIR)"
        )
    return run_reindex(directory, _db_path())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
