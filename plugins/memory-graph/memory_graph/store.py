"""Local SQLite store: doc metadata, embeddings, and [[link]] graph edges.

Vector search prefers `sqlite-vec` (a loadable SQLite extension) and falls
back to brute-force numpy cosine similarity — computed in-process over the
embeddings stored as BLOBs — when the extension can't be loaded (common on
stock macOS/homebrew Python builds where `enable_load_extension` is
unavailable or the extension fails a self-test). At the scale of a personal
memory corpus (tens to low thousands of docs) brute force is effectively
instant, so either path satisfies the tool's functional requirements.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np

from .embed import EMBED_DIM
from .model import MemoryDoc

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    name TEXT PRIMARY KEY,
    description TEXT,
    type TEXT,
    body TEXT,
    path TEXT,
    mtime REAL,
    hash TEXT,
    embedding BLOB,
    dim INTEGER
);
CREATE TABLE IF NOT EXISTS links (
    source TEXT NOT NULL,
    target_raw TEXT NOT NULL,
    target_resolved TEXT
);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_resolved);
"""


def _normalize(text: str) -> str:
    """Loose key for fuzzy name resolution: lowercase, alnum-only."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def default_db_path() -> str:
    """Where the index lives when --db isn't passed explicitly.

    Thin wrapper around `config.resolve_db_path()` — kept here for backward
    compatibility since callers historically imported it from `store`. This
    is a derived artifact (safe to delete/rebuild) — never the markdown
    source of truth.
    """
    from .config import resolve_db_path

    return resolve_db_path()


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self.use_vec = self._try_init_vec_extension()

    # ------------------------------------------------------------------
    # sqlite-vec extension (optional fast path)
    # ------------------------------------------------------------------
    def _try_init_vec_extension(self) -> bool:
        try:
            import sqlite_vec  # noqa: F401
        except ImportError:
            return False

        try:
            self.conn.enable_load_extension(True)
            sqlite_vec.load(self.conn)
            self.conn.enable_load_extension(False)
            self.conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_index "
                f"USING vec0(embedding float[{EMBED_DIM}] distance_metric=cosine)"
            )
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS vec_map "
                "(rowid INTEGER PRIMARY KEY, name TEXT UNIQUE)"
            )
            self.conn.commit()
            # Self-test: insert + query a throwaway vector end to end.
            probe = np.ones(EMBED_DIM, dtype=np.float32)
            blob = sqlite_vec.serialize_float32(probe.tolist())
            self.conn.execute(
                "INSERT INTO vec_index(rowid, embedding) VALUES (-1, ?)", (blob,)
            )
            row = self.conn.execute(
                "SELECT rowid FROM vec_index WHERE embedding MATCH ? "
                "ORDER BY distance LIMIT 1",
                (blob,),
            ).fetchone()
            self.conn.execute("DELETE FROM vec_index WHERE rowid = -1")
            self.conn.commit()
            if row is None:
                return False
            self._sqlite_vec = sqlite_vec
            return True
        except (AttributeError, sqlite3.OperationalError, sqlite3.DatabaseError):
            try:
                self.conn.execute("DROP TABLE IF EXISTS vec_index")
                self.conn.execute("DROP TABLE IF EXISTS vec_map")
                self.conn.commit()
            except sqlite3.Error:
                pass
            return False

    # ------------------------------------------------------------------
    # Doc metadata + embeddings
    # ------------------------------------------------------------------
    def get_hash(self, name: str) -> str | None:
        row = self.conn.execute(
            "SELECT hash FROM docs WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None

    def upsert_doc_meta(self, doc: MemoryDoc) -> None:
        """Insert/update everything except the embedding column."""
        self.conn.execute(
            """
            INSERT INTO docs (name, description, type, body, path, mtime, hash)
            VALUES (:name, :description, :type, :body, :path, :mtime, :hash)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                type = excluded.type,
                body = excluded.body,
                path = excluded.path,
                mtime = excluded.mtime,
                hash = excluded.hash
            """,
            {
                "name": doc.name,
                "description": doc.description,
                "type": doc.type,
                "body": doc.body,
                "path": doc.path,
                "mtime": doc.mtime,
                "hash": doc.hash,
            },
        )

    def set_embedding(self, name: str, vector: np.ndarray) -> None:
        vector = np.asarray(vector, dtype=np.float32)
        blob = vector.tobytes()
        self.conn.execute(
            "UPDATE docs SET embedding = ?, dim = ? WHERE name = ?",
            (blob, vector.shape[0], name),
        )
        if self.use_vec:
            self._vec_upsert(name, vector)

    def _vec_upsert(self, name: str, vector: np.ndarray) -> None:
        existing = self.conn.execute(
            "SELECT rowid FROM vec_map WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            self.conn.execute(
                "DELETE FROM vec_index WHERE rowid = ?", (existing[0],)
            )
            rowid = existing[0]
        else:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(rowid), 0) + 1 FROM vec_map"
            ).fetchone()
            rowid = row[0]
            self.conn.execute(
                "INSERT INTO vec_map(rowid, name) VALUES (?, ?)", (rowid, name)
            )
        blob = self._sqlite_vec.serialize_float32(vector.tolist())
        self.conn.execute(
            "INSERT INTO vec_index(rowid, embedding) VALUES (?, ?)", (rowid, blob)
        )

    def prune_missing(self, current_names: set[str]) -> None:
        rows = self.conn.execute("SELECT name FROM docs").fetchall()
        stale = [r[0] for r in rows if r[0] not in current_names]
        for name in stale:
            self.conn.execute("DELETE FROM docs WHERE name = ?", (name,))
            if self.use_vec:
                row = self.conn.execute(
                    "SELECT rowid FROM vec_map WHERE name = ?", (name,)
                ).fetchone()
                if row:
                    self.conn.execute(
                        "DELETE FROM vec_index WHERE rowid = ?", (row[0],)
                    )
                    self.conn.execute(
                        "DELETE FROM vec_map WHERE name = ?", (name,)
                    )

    def get(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT name, description, type, body, path, mtime FROM docs "
            "WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            return None
        return {
            "name": row[0],
            "description": row[1],
            "type": row[2],
            "body": row[3],
            "path": row[4],
            "mtime": row[5],
        }

    def all_names(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT name FROM docs")]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    # ------------------------------------------------------------------
    # Name resolution (handles messy real-world corpora where a [[link]]
    # or a CLI query doesn't exactly match the frontmatter `name:`).
    # ------------------------------------------------------------------
    def resolve(self, query: str) -> str | None:
        if not query:
            return None
        query = query.strip()

        row = self.conn.execute(
            "SELECT name FROM docs WHERE name = ?", (query,)
        ).fetchone()
        if row:
            return row[0]

        # Match by filename stem (memory files are often referenced by
        # their filename even when the frontmatter `name:` differs).
        for name, path in self.conn.execute("SELECT name, path FROM docs"):
            if Path(path).stem == query:
                return name

        # Loose normalized match (case/hyphen/underscore-insensitive) on
        # both the frontmatter name and the filename stem.
        norm_query = _normalize(query)
        for name, path in self.conn.execute("SELECT name, path FROM docs"):
            if _normalize(name) == norm_query or _normalize(Path(path).stem) == norm_query:
                return name

        return None

    # ------------------------------------------------------------------
    # Link graph
    # ------------------------------------------------------------------
    def clear_links(self) -> None:
        self.conn.execute("DELETE FROM links")

    def add_link(self, source: str, target_raw: str, target_resolved: str | None) -> None:
        self.conn.execute(
            "INSERT INTO links (source, target_raw, target_resolved) VALUES (?, ?, ?)",
            (source, target_raw, target_resolved),
        )

    def outgoing(self, name: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT target_resolved FROM links "
            "WHERE source = ? AND target_resolved IS NOT NULL",
            (name,),
        ).fetchall()
        return [r[0] for r in rows]

    def incoming(self, name: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT source FROM links WHERE target_resolved = ?",
            (name,),
        ).fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Vector search
    # ------------------------------------------------------------------
    def vector_search(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        if self.use_vec:
            try:
                return self._vector_search_vec(query_vec, k)
            except (sqlite3.Error, AttributeError):
                self.use_vec = False
        return self._vector_search_numpy(query_vec, k)

    def _vector_search_vec(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        blob = self._sqlite_vec.serialize_float32(
            np.asarray(query_vec, dtype=np.float32).tolist()
        )
        rows = self.conn.execute(
            "SELECT rowid, distance FROM vec_index WHERE embedding MATCH ? "
            "ORDER BY distance LIMIT ?",
            (blob, k),
        ).fetchall()
        results = []
        for rowid, distance in rows:
            name_row = self.conn.execute(
                "SELECT name FROM vec_map WHERE rowid = ?", (rowid,)
            ).fetchone()
            if name_row:
                # cosine distance -> cosine similarity, same scale as the
                # numpy fallback's score.
                results.append((name_row[0], 1.0 - float(distance)))
        return results

    def _vector_search_numpy(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            "SELECT name, embedding FROM docs WHERE embedding IS NOT NULL"
        ).fetchall()
        if not rows:
            return []
        names = [r[0] for r in rows]
        mat = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
        q = np.asarray(query_vec, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-9)
        mat_norm = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
        sims = mat_norm @ q_norm
        order = np.argsort(-sims)[:k]
        return [(names[i], float(sims[i])) for i in order]

    def close(self) -> None:
        self.conn.close()
