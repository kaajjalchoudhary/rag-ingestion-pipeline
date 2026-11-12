from pathlib import Path

from ragprep import HashingEmbedder, Index

EXAMPLES = Path(__file__).parent.parent / "examples" / "docs"

POLICY = (
    "Customers can request a full refund within thirty days of delivery if the item is unused.\n\n"
    "Express shipping delivers the next business day when you order before two in the afternoon."
)


class CountingEmbedder(HashingEmbedder):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return super().embed(texts)


def make_index():
    embedder = CountingEmbedder()
    return Index(embedder=embedder, max_words=20, overlap_words=0), embedder


def test_second_sync_of_same_documents_does_no_work():
    index, embedder = make_index()
    first = index.sync({"policy.md": POLICY})
    assert first.added == 1 and first.chunks_embedded == 2
    second = index.sync({"policy.md": POLICY})
    assert second.unchanged == 1 and second.chunks_embedded == 0
    assert embedder.calls == 2


def test_editing_one_paragraph_only_reembeds_that_chunk():
    index, embedder = make_index()
    index.sync({"policy.md": POLICY})
    edited = POLICY.replace("thirty days", "sixty days")
    stats = index.sync({"policy.md": edited})
    assert stats.updated == 1
    assert stats.chunks_embedded == 1 and stats.chunks_reused == 1
    assert embedder.calls == 3
    assert index.counts() == {"documents": 1, "chunks": 2, "embeddings": 2}


def test_removed_documents_are_deleted_with_their_chunks_and_vectors():
    index, _ = make_index()
    index.sync({"a.md": POLICY, "b.md": "A different document about warranty claims and repairs."})
    stats = index.sync({"b.md": "A different document about warranty claims and repairs."})
    assert stats.deleted == 1
    assert index.counts() == {"documents": 1, "chunks": 1, "embeddings": 1}


def test_identical_chunks_across_documents_are_indexed_once():
    index, _ = make_index()
    stats = index.sync({"a.md": POLICY, "copy.md": POLICY})
    assert stats.duplicate_chunks_skipped == 2
    assert index.counts()["chunks"] == 2


def test_search_finds_the_relevant_document(tmp_path):
    index = Index(tmp_path / "index.sqlite")
    stats = index.sync_folder(EXAMPLES)
    assert stats.added == 3
    assert index.search("how long does express shipping take", k=1)[0].doc_id == "shipping.md"
    assert index.search("can I get my money back", k=1)[0].doc_id == "refund-policy.md"
    assert index.search("warranty claim for a broken device", k=1)[0].doc_id == "warranty.txt"


def test_pii_never_reaches_the_index(tmp_path):
    index = Index(tmp_path / "index.sqlite")
    index.sync_folder(EXAMPLES)
    texts = " ".join(row[0] for row in index.db.execute("SELECT text FROM chunks"))
    assert "support@example.com" not in texts and "7946" not in texts
    assert "[EMAIL]" in texts and "[PHONE]" in texts


def test_index_persists_between_runs(tmp_path):
    db = tmp_path / "index.sqlite"
    Index(db).sync_folder(EXAMPLES)
    assert Index(db).sync_folder(EXAMPLES).unchanged == 3
