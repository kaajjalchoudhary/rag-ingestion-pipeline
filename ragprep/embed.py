"""Embedders. The default HashingEmbedder needs no model download, so pipelines and CI stay offline."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, Sequence

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Feature-hashed unigrams and bigrams, L2-normalised. Deterministic across runs and machines."""

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.name = f"hashing-{dim}"

    def _bucket(self, token: str) -> tuple[int, float]:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        return value % self.dim, 1.0 if (value >> 63) & 1 else -1.0

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            tokens = _TOKEN.findall(text.lower())
            features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
            vec = [0.0] * self.dim
            for feature in features:
                idx, sign = self._bucket(feature)
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
