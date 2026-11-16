# Changelog

All notable changes to ragprep are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
