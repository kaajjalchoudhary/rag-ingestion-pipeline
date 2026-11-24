# Changelog

All notable changes to ragprep are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `ragprep stats`: document, chunk and embedding counts, plus how many chunks each embedding model
  covers.
- `ragprep ingest --exclude PATTERN` (and `exclude=` on `Index.sync_folder`) to skip files by their path
  inside the folder. Excluded files that were already indexed are removed.

### Fixed
- Switching to a different embedder now embeds the chunks of unchanged documents once. Before, they were
  skipped, so they had no vectors for the new model and search returned nothing.

## [0.1.0] - 2026-11-17

First release.

### Added
- `ragprep ingest`: cleans, PII-redacts, chunks on paragraph and sentence boundaries, deduplicates and
  syncs documents into a SQLite vector index incrementally. Unchanged documents are skipped, an edited
  paragraph re-embeds one chunk and deleted files are removed from the index.
- `ragprep search`: top-k retrieval over the index.
- Embeddings cached per chunk hash and model; pluggable embedders, offline by default.
- Wheel and source distribution attached to the GitHub release, and a container image on GitHub
  Packages (`ghcr.io/kaajjalchoudhary/ragprep`).
