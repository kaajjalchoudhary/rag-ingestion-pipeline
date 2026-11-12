"""SQLite-backed vector index with incremental sync.

Sync rules:
- a document whose content hash is unchanged is skipped entirely;
- a changed document has its chunks rebuilt, but only chunks with a new text hash are embedded
  (embeddings are cached by chunk hash, so moving a paragraph costs nothing);
- documents that disappeared from the source are deleted with their chunks;
- chunks whose exact text already exists in another document are not indexed twice.
"""

from __future__ import annotations

import hashlib
import sqlite3
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ragprep.chunking import chunk_text
from ragprep.embed import Embedder, HashingEmbedder, cosine

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, position INTEGER NOT NULL,
    text TEXT NOT NULL, chunk_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_by_hash ON chunks (chunk_hash);
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_hash TEXT NOT NULL, model TEXT NOT NULL, vector BLOB NOT NULL,
    PRIMARY KEY (chunk_hash, model)
);
"""


@dataclass
class SyncStats:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0
    chunks_embedded: int = 0
    chunks_reused: int = 0
    duplicate_chunks_skipped: int = 0


@dataclass
class Hit:
    doc_id: str
    chunk_id: str
    score: float
    text: str


class Index:
    def __init__(self, path: str | Path = ":memory:", embedder: Embedder | None = None, **chunk_opts):
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)
        self.embedder = embedder or HashingEmbedder()
        self.chunk_opts = chunk_opts

    def sync(self, documents: dict[str, str]) -> SyncStats:
        """Make the index match `documents` (doc_id -> text) exactly."""
        stats = SyncStats()
        known = dict(self.db.execute("SELECT doc_id, content_hash FROM documents"))
        with self.db:
            for doc_id in sorted(set(known) - set(documents)):
                self._delete(doc_id)
                stats.deleted += 1
            for doc_id in sorted(documents):
                content_hash = hashlib.sha256(documents[doc_id].encode()).hexdigest()
                if known.get(doc_id) == content_hash:
                    stats.unchanged += 1
                    continue
                if doc_id in known:
                    self._delete(doc_id)
                    stats.updated += 1
                else:
                    stats.added += 1
                self._insert(doc_id, documents[doc_id], content_hash, stats)
            self._gc_embeddings()
        return stats

    def sync_folder(self, folder: str | Path, patterns: Iterable[str] = ("*.md", "*.txt")) -> SyncStats:
        root = Path(folder)
        docs = {
            p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for pattern in patterns
            for p in root.rglob(pattern)
        }
        return self.sync(docs)

    def _delete(self, doc_id: str) -> None:
        self.db.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

    def _insert(self, doc_id: str, text: str, content_hash: str, stats: SyncStats) -> None:
        self.db.execute("INSERT INTO documents VALUES (?, ?)", (doc_id, content_hash))
        model = self.embedder.name
        to_embed: dict[str, str] = {}
        for chunk in chunk_text(doc_id, text, **self.chunk_opts):
            h = chunk.chunk_hash
            if self.db.execute("SELECT 1 FROM chunks WHERE chunk_hash = ?", (h,)).fetchone():
                stats.duplicate_chunks_skipped += 1
                continue
            self.db.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
                (chunk.chunk_id, doc_id, chunk.position, chunk.text, h),
            )
            cached = self.db.execute(
                "SELECT 1 FROM embeddings WHERE chunk_hash = ? AND model = ?", (h, model)
            ).fetchone()
            if cached:
                stats.chunks_reused += 1
            else:
                to_embed[h] = chunk.text
        if to_embed:
            vectors = self.embedder.embed(list(to_embed.values()))
            self.db.executemany(
                "INSERT INTO embeddings VALUES (?, ?, ?)",
                [(h, model, array("f", v).tobytes()) for h, v in zip(to_embed, vectors)],
            )
            stats.chunks_embedded += len(to_embed)

    def _gc_embeddings(self) -> None:
        # Runs once per sync, after all inserts, so vectors of chunks that only moved are reused first.
        self.db.execute("DELETE FROM embeddings WHERE chunk_hash NOT IN (SELECT chunk_hash FROM chunks)")

    def search(self, query: str, k: int = 3) -> list[Hit]:
        qvec = self.embedder.embed([query])[0]
        rows = self.db.execute(
            "SELECT c.doc_id, c.chunk_id, c.text, e.vector FROM chunks c "
            "JOIN embeddings e ON e.chunk_hash = c.chunk_hash AND e.model = ?",
            (self.embedder.name,),
        )
        hits = [
            Hit(doc_id, chunk_id, cosine(qvec, array("f", blob)), text)
            for doc_id, chunk_id, text, blob in rows
        ]
        return sorted(hits, key=lambda h: h.score, reverse=True)[:k]

    def counts(self) -> dict[str, int]:
        q = lambda t: self.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: E731
        return {"documents": q("documents"), "chunks": q("chunks"), "embeddings": q("embeddings")}
