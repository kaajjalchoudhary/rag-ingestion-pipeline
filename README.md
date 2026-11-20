# RAG Ingestion Pipeline

[![ci](https://github.com/kaajjalchoudhary/rag-ingestion-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kaajjalchoudhary/rag-ingestion-pipeline/actions/workflows/ci.yml)

Most RAG demos re-embed every document on every run. This is the data-engineering side of RAG:
a small, dependency-free pipeline (`ragprep`) that turns a folder of documents into a clean vector
index and keeps it in sync **incrementally**, the same way you would treat any other table.

```
docs/ ──► clean (NFKC, whitespace, PII redaction) ──► chunk (paragraph → sentence → words, with overlap)
      ──► dedupe (exact chunk hash) ──► embed only new chunk hashes ──► SQLite index ──► search
```

## What it guarantees

| Rule | How |
|---|---|
| Re-running on unchanged docs does no work | each document is skipped when its content hash matches |
| Editing one paragraph re-embeds one chunk | embeddings are cached by chunk text hash, not by document |
| Deleted source files leave nothing behind | docs missing from the source are removed with their chunks and orphaned vectors |
| The same text is never indexed twice | identical chunks across documents are skipped |
| No emails or phone numbers reach the vector store | redacted to `[EMAIL]` / `[PHONE]` before chunking |
| Runs offline and in CI | default `HashingEmbedder` is deterministic and needs no model download; any embedder with `name`, `dim` and `embed(texts)` plugs in |

Every rule above has a test in [`tests/`](tests), and CI also runs the pipeline end to end on
[`examples/docs`](examples/docs) and checks that the second run is a no-op.

## Quick start

```bash
pip install https://github.com/kaajjalchoudhary/rag-ingestion-pipeline/releases/download/v0.1.0/ragprep-0.1.0-py3-none-any.whl
# or: pip install git+https://github.com/kaajjalchoudhary/rag-ingestion-pipeline.git
# or: docker run --rm -v "$PWD:/data" ghcr.io/kaajjalchoudhary/ragprep ingest docs --db index.sqlite
ragprep ingest examples/docs --db index.sqlite
# added=3 updated=0 unchanged=0 deleted=0 chunks_embedded=3 ...
ragprep ingest examples/docs --db index.sqlite
# added=0 updated=0 unchanged=3 deleted=0 chunks_embedded=0 ...
ragprep search "can I return a damaged item" --db index.sqlite
```

From Python:

```python
from ragprep import Index

index = Index("index.sqlite", max_words=120, overlap_words=20)
# index the whole folder (*.md, *.txt); files no longer in it are removed from the index
stats = index.sync_folder("examples/docs")
# or pass the full set yourself: index.sync({"faq.md": text, ...})
for hit in index.search("refund window", k=3):
    print(hit.score, hit.chunk_id, hit.text)
```

## Using a real embedding model

```python
from sentence_transformers import SentenceTransformer

class STEmbedder:
    def __init__(self, model="all-MiniLM-L6-v2"):
        self.model, self.name, self.dim = SentenceTransformer(model), model, 384
    def embed(self, texts):
        return self.model.encode(list(texts), normalize_embeddings=True).tolist()

index = Index("index.sqlite", embedder=STEmbedder())
```

Vectors are stored per `(chunk_hash, model)`, so switching models re-embeds once and never mixes vectors.

## Layout

```
ragprep/chunking.py   cleaning, PII redaction, boundary-aware chunking
ragprep/embed.py      Embedder protocol + offline HashingEmbedder
ragprep/index.py      SQLite schema, incremental sync, search
ragprep/cli.py        `ragprep ingest` / `ragprep search`
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Requires Python 3.10+. The package itself has no runtime dependencies; `pytest` is the only dev dependency.
CI runs the tests on Python 3.10 and 3.12, then the end-to-end ingest and search check on `examples/docs`.
