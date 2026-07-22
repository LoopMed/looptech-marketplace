"""Incremental reindexing: parse -> (only changed) embed -> store.

Markdown files are the source of truth. This module never writes to them —
it only reads the directory and writes derived data into the SQLite index.
"""

from __future__ import annotations

from .embed import Embedder
from .parse import scan_dir
from .store import Store


def reindex_store(store: Store, directory: str) -> dict:
    """Same incremental logic as `reindex()`, but reuses an already-open
    `Store` instead of opening/closing its own connection.

    This is what both the explicit `reindex` command/tool and the lazy
    `ensure_fresh()` (called at the top of every query) share — there is
    only one hash/mtime-based incremental algorithm.

    Returns a stats dict: {"total", "embedded", "skipped", "removed"}.
    """
    docs = scan_dir(directory)

    embedder: Embedder | None = None
    embedded = 0
    skipped = 0

    for doc in docs:
        previous_hash = store.get_hash(doc.name)
        store.upsert_doc_meta(doc)
        if previous_hash != doc.hash:
            if embedder is None:
                embedder = Embedder()
            text = doc.body or doc.description or doc.name
            vector = embedder.embed_one(text)
            store.set_embedding(doc.name, vector)
            embedded += 1
        else:
            skipped += 1

    current_names = {doc.name for doc in docs}
    before = set(store.all_names())
    store.prune_missing(current_names)
    removed = len(before - current_names)

    store.clear_links()
    for doc in docs:
        for target_raw in doc.links:
            resolved = store.resolve(target_raw)
            store.add_link(doc.name, target_raw, resolved)

    store.conn.commit()

    return {
        "total": len(docs),
        "embedded": embedded,
        "skipped": skipped,
        "removed": removed,
    }


def reindex(directory: str, db_path: str) -> dict:
    """Reindex `directory` into the SQLite store at `db_path`.

    Opens and closes its own `Store` connection — the entrypoint used by
    the explicit `reindex` CLI command / `memory_reindex` MCP tool.
    """
    store = Store(db_path)
    try:
        return reindex_store(store, directory)
    finally:
        store.close()


def ensure_fresh(store: Store, memory_dir: str | None) -> dict | None:
    """Lazily bring `store` up to date with `memory_dir` before a query.

    Called at the start of every `search` / `get` / `neighbors` entrypoint
    (CLI and MCP alike) so nobody has to run `reindex` by hand. It's the
    same incremental algorithm as the explicit reindex — only files whose
    content hash changed get re-embedded — so the cost is ~ms when nothing
    changed and proportional only to what actually changed otherwise.

    No-ops (returns `None`) when `memory_dir` couldn't be resolved, so a
    query still runs against whatever is already in the index.
    """
    if not memory_dir:
        return None
    return reindex_store(store, memory_dir)
