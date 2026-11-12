import pytest

from ragprep.chunking import chunk_text, clean_text


def test_clean_text_normalises_whitespace_and_redacts_pii():
    raw = "Mail  jane.doe@example.com\r\nor call +44 20 7946 0958.\n\n\n\nNext   para"
    assert clean_text(raw) == "Mail [EMAIL] or call [PHONE].\n\nNext para"
    assert "jane.doe@example.com" in clean_text(raw, redact_pii=False)


def test_chunks_respect_max_words_and_overlap():
    text = " ".join(f"Sentence number {i} is here." for i in range(100))
    chunks = chunk_text("doc", text, max_words=50, overlap_words=10)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 50 for c in chunks)
    for prev, nxt in zip(chunks, chunks[1:]):
        assert prev.text.split()[-10:] == nxt.text.split()[:10]


def test_short_paragraphs_are_packed_and_tiny_chunks_dropped():
    text = "First paragraph has six words.\n\nSecond one is also short."
    chunks = chunk_text("doc", text, max_words=50, overlap_words=0)
    assert [c.text for c in chunks] == ["First paragraph has six words. Second one is also short."]
    assert chunk_text("doc", "too short", min_words=5) == []


def test_chunk_ids_and_hashes_are_stable():
    a = chunk_text("doc", "the same text repeated " * 20, max_words=30, overlap_words=5)
    b = chunk_text("doc", "the same text repeated " * 20, max_words=30, overlap_words=5)
    assert [c.chunk_id for c in a] == [f"doc#{i}" for i in range(len(a))]
    assert [c.chunk_hash for c in a] == [c.chunk_hash for c in b]


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_text("doc", "x", max_words=10, overlap_words=10)
