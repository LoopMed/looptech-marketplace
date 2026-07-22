"""Incremental reindexing: parse -> (only changed) embed -> store.

Markdown files are the source of truth. This module never writes to them —
it only reads the directory and writes derived data into the SQLite index.
"""

from __future__ import annotations

from .embed import Embedder
from .parse import scan_dir
from .store import Store


def reindex(directory: str, db_path: str) -> dict:
    """Reindex `directory` into the SQLite store at `db_path`.

    Returns a stats dict: {"total", "embedded", "skipped", "removed"}.
    """
    docs = scan_dir(directory)
    store = Store(db_path)

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
    store.close()

    return {
        "total": len(docs),
        "embedded": embedded,
        "skipped": skipped,
        "removed": removed,
    }
