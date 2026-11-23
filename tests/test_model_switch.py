from ragprep import HashingEmbedder, Index

POLICY = (
    "Customers can request a full refund within thirty days of delivery if the item is unused.\n\n"
    "Express shipping delivers the next business day when you order before two in the afternoon."
)


class CountingEmbedder(HashingEmbedder):
    def __init__(self, dim=256):
        super().__init__(dim)
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return super().embed(texts)


def open_index(db, embedder=None):
    return Index(db, embedder=embedder, max_words=20, overlap_words=0)


def test_switching_embedder_reembeds_unchanged_documents_once(tmp_path):
    db = tmp_path / "index.sqlite"
    open_index(db).sync({"policy.md": POLICY})

    new_model = CountingEmbedder(dim=128)
    index = open_index(db, new_model)
    stats = index.sync({"policy.md": POLICY})
    assert stats.unchanged == 1 and stats.chunks_embedded == 2
    assert index.sync({"policy.md": POLICY}).chunks_embedded == 0
    assert new_model.calls == 2


def test_search_after_switching_embedder_uses_only_the_new_model(tmp_path):
    db = tmp_path / "index.sqlite"
    open_index(db).sync({"policy.md": POLICY})
    index = open_index(db, HashingEmbedder(dim=128))
    index.sync({"policy.md": POLICY})
    # vectors for both models are kept side by side, keyed by (chunk_hash, model)
    assert index.counts() == {"documents": 1, "chunks": 2, "embeddings": 4}
    hits = index.search("can I get a refund", k=5)
    assert len(hits) == 2
    assert hits[0].chunk_id == "policy.md#0"
