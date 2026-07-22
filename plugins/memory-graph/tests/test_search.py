from pathlib import Path

from memory_graph.embed import Embedder
from memory_graph.index import ensure_fresh, reindex
from memory_graph.search import get, neighbors, search
from memory_graph.store import Store

DOC_A = """---
name: payment-gateway-integration
description: Integrating a new payment gateway for processing transactions.
metadata:
  type: project
---
We integrated a new payment gateway to process credit card and PIX
transactions securely. See [[payment-gateway-incident]] for a related
outage.
"""

DOC_B = """---
name: payment-gateway-incident
description: An incident where the payment gateway had downtime.
metadata:
  type: project
---
The payment gateway had unexpected downtime last week, causing failed
transactions. Related to [[payment-gateway-integration]].
"""

DOC_C = """---
name: sourdough-bread-recipe
description: How to bake sourdough bread at home.
metadata:
  type: reference
---
Mix flour, water, salt and starter. Let the dough ferment overnight before
baking sourdough bread in a hot oven.
"""


def _build_index(tmp_path: Path):
    (tmp_path / "a.md").write_text(DOC_A, encoding="utf-8")
    (tmp_path / "b.md").write_text(DOC_B, encoding="utf-8")
    (tmp_path / "c.md").write_text(DOC_C, encoding="utf-8")
    db_path = str(tmp_path / "index.db")
    stats = reindex(str(tmp_path), db_path)
    return db_path, stats


def test_reindex_embeds_all_then_incremental_skips_unchanged(tmp_path: Path):
    db_path, stats = _build_index(tmp_path)
    assert stats["total"] == 3
    assert stats["embedded"] == 3
    assert stats["skipped"] == 0

    stats2 = reindex(str(tmp_path), db_path)
    assert stats2["total"] == 3
    assert stats2["embedded"] == 0
    assert stats2["skipped"] == 3


def test_search_returns_semantically_relevant_doc(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        results = search(
            store, Embedder(), "credit card transaction processing outage", k=2
        )
    finally:
        store.close()

    assert len(results) == 2
    top_names = {r["name"] for r in results}
    assert top_names == {"payment-gateway-integration", "payment-gateway-incident"}
    assert results[0]["name"] in top_names  # sanity: has a name at all
    assert "sourdough-bread-recipe" not in top_names


def test_get_resolves_by_name(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        doc = get(store, "payment-gateway-integration")
    finally:
        store.close()
    assert doc is not None
    assert doc["description"].startswith("Integrating")


def test_get_unknown_name_returns_none(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        doc = get(store, "does-not-exist")
    finally:
        store.close()
    assert doc is None


def test_neighbors_follows_links(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        result = neighbors(store, "payment-gateway-integration", depth=1)
    finally:
        store.close()

    assert result["resolved"] == "payment-gateway-integration"
    neighbor_names = {d["name"] for d in result["neighbors"]}
    assert neighbor_names == {"payment-gateway-incident"}


def test_neighbors_resolves_by_filename_stem(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        # file is a.md but frontmatter name is payment-gateway-integration
        result = neighbors(store, "a", depth=1)
    finally:
        store.close()
    assert result["resolved"] == "payment-gateway-integration"


def test_neighbors_unresolved_name_returns_empty(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        result = neighbors(store, "does-not-exist", depth=1)
    finally:
        store.close()
    assert result["resolved"] is None
    assert result["neighbors"] == []


def test_ensure_fresh_reflects_file_edits_without_manual_reindex(tmp_path: Path):
    """The lazy-reindex helper every query entrypoint calls at the top of
    search/get/neighbors: editing a memory file and calling only
    `ensure_fresh()` (never the explicit `reindex()`) must be enough for a
    subsequent query to see the new content.
    """
    doc_path = tmp_path / "a.md"
    doc_path.write_text(DOC_A, encoding="utf-8")
    db_path = str(tmp_path / "index.db")
    store = Store(db_path)
    try:
        first = ensure_fresh(store, str(tmp_path))
        assert first["embedded"] == 1

        doc = get(store, "payment-gateway-integration")
        assert doc is not None
        assert "3D Secure" not in doc["description"]

        # Edit the source .md directly, as a user would — no explicit
        # `reindex()` call anywhere in this test.
        edited = DOC_A.replace(
            "Integrating a new payment gateway for processing transactions.",
            "Integrating a new payment gateway for processing transactions, now with 3D Secure.",
        )
        doc_path.write_text(edited, encoding="utf-8")

        second = ensure_fresh(store, str(tmp_path))
        assert second["embedded"] == 1  # only the changed file was re-embedded
        assert second["skipped"] == 0

        doc_after = get(store, "payment-gateway-integration")
        assert doc_after is not None
        assert "3D Secure" in doc_after["description"]
    finally:
        store.close()


def test_ensure_fresh_is_noop_without_a_memory_dir(tmp_path: Path):
    db_path, _ = _build_index(tmp_path)
    store = Store(db_path)
    try:
        assert ensure_fresh(store, None) is None
    finally:
        store.close()
