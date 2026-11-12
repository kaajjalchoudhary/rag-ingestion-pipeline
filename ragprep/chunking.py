"""Clean and split text into overlapping chunks that respect paragraph and sentence boundaries."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    position: int
    text: str

    @property
    def chunk_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}#{self.position}"


def clean_text(text: str, redact_pii: bool = True) -> str:
    """Normalise unicode, collapse whitespace inside paragraphs and optionally redact emails/phones."""
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n")
    if redact_pii:
        text = _EMAIL.sub("[EMAIL]", text)
        text = _PHONE.sub("[PHONE]", text)
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)


def _units(text: str, max_words: int) -> list[str]:
    """Break text into units no longer than max_words: paragraphs, then sentences, then word windows."""
    units: list[str] = []
    for para in text.split("\n\n"):
        if len(para.split()) <= max_words:
            units.append(para)
            continue
        for sentence in _SENTENCE_END.split(para):
            words = sentence.split()
            for start in range(0, len(words), max_words):
                units.append(" ".join(words[start : start + max_words]))
    return [u for u in units if u.strip()]


def chunk_text(
    doc_id: str,
    text: str,
    max_words: int = 120,
    overlap_words: int = 20,
    min_words: int = 5,
    redact_pii: bool = True,
) -> list[Chunk]:
    """Greedily pack units into chunks of at most max_words, carrying overlap_words into the next chunk."""
    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words")
    cleaned = clean_text(text, redact_pii=redact_pii)
    chunks: list[str] = []
    current: list[str] = []
    for unit in _units(cleaned, max_words - overlap_words):
        words = unit.split()
        if current and len(current) + len(words) > max_words:
            chunks.append(" ".join(current))
            current = current[-overlap_words:] if overlap_words else []
        current.extend(words)
    if current:
        chunks.append(" ".join(current))
    kept = [c for c in chunks if len(c.split()) >= min_words]
    return [Chunk(doc_id, i, c) for i, c in enumerate(kept)]
