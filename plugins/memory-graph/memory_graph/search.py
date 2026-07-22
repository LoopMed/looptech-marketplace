"""Query-time operations over an already-built index: semantic search,
single-doc lookup, and graph neighbor traversal.
"""

from __future__ import annotations

from .embed import Embedder
from .store import Store


def search(store: Store, embedder: Embedder, query: str, k: int = 5) -> list[dict]:
    """Semantic (vector) search — ranks by embedding similarity, not keywords."""
    vector = embedder.embed_one(query)
    hits = store.vector_search(vector, k)
    results = []
    for name, score in hits:
        doc = store.get(name)
        if doc is None:
            continue
        results.append(
            {
                "name": doc["name"],
                "score": score,
                "description": doc["description"],
                "type": doc["type"],
                "path": doc["path"],
            }
        )
    return results


def get(store: Store, name: str) -> dict | None:
    """Fetch a single memory by name (with fuzzy fallback resolution)."""
    resolved = store.resolve(name)
    if resolved is None:
        return None
    return store.get(resolved)


def neighbors(store: Store, name: str, depth: int = 1) -> dict:
    """Traverse the `[[link]]` graph from `name` out to `depth` hops.

    Traversal is undirected: both docs `name` links to, and docs that link
    to `name`, count as neighbors — this matches how a human recalls related
    memories regardless of which file happened to declare the link.
    """
    resolved = store.resolve(name)
    if resolved is None:
        return {"query": name, "resolved": None, "neighbors": []}

    visited = {resolved}
    frontier = {resolved}
    ordered: list[str] = []

    for _ in range(max(depth, 0)):
        next_frontier: set[str] = set()
        for node in frontier:
            for target in store.outgoing(node):
                if target not in visited:
                    next_frontier.add(target)
            for source in store.incoming(node):
                if source not in visited:
                    next_frontier.add(source)
        next_frontier -= visited
        visited |= next_frontier
        ordered.extend(sorted(next_frontier))
        frontier = next_frontier
        if not frontier:
            break

    docs = []
    for n in ordered:
        doc = store.get(n)
        if doc:
            docs.append(doc)

    return {"query": name, "resolved": resolved, "neighbors": docs}
