"""ragprep: turn a folder of documents into a clean, incrementally maintained vector index."""

from ragprep.chunking import Chunk, chunk_text
from ragprep.embed import HashingEmbedder
from ragprep.index import Index, SyncStats

__all__ = ["Chunk", "chunk_text", "HashingEmbedder", "Index", "SyncStats"]
__version__ = "0.1.0"
