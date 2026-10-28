"""Retrievers: a lexical BM25 baseline and the primary dense (Gemini + Chroma) index.

Both expose the same ``retrieve(query, k)`` method returning ``RetrievedChunk``
objects sorted by score, so the generator does not care which one it gets.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Protocol, Sequence

from .chunking import Chunk
from .config import SETTINGS, require_env

# Definitions live in concept pages and worked examples; end-of-chapter pages
# repeat the same keywords as *questions*, so they are gently down-weighted.
CONTENT_TYPE_BOOST = {
    "concept": 1.3,
    "worked_example": 1.2,
    "activity": 1.0,
    "end_of_chapter": 0.8,
}


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = SETTINGS.top_k) -> list[RetrievedChunk]: ...


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, used identically for index and query."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()


class BM25Retriever:
    def __init__(self, chunks: Sequence[Chunk], boost: dict | None = None):
        from rank_bm25 import BM25Okapi

        self.chunks = list(chunks)
        self.boost = CONTENT_TYPE_BOOST if boost is None else boost
        self._index = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def retrieve(self, query: str, k: int = SETTINGS.top_k) -> list[RetrievedChunk]:
        scores = self._index.get_scores(tokenize(query))
        weighted = [
            score * self.boost.get(chunk.content_type, 1.0)
            for chunk, score in zip(self.chunks, scores)
        ]
        ranked = sorted(range(len(self.chunks)), key=weighted.__getitem__, reverse=True)
        return [RetrievedChunk(self.chunks[i], round(float(weighted[i]), 4)) for i in ranked[:k]]


class DenseRetriever:
    """Gemini embeddings stored in a persistent Chroma collection (cosine)."""

    def __init__(
        self,
        chunks: Sequence[Chunk],
        embed_model: str = SETTINGS.embed_model,
        collection_name: str = SETTINGS.collection_name,
        persist_dir=SETTINGS.chroma_dir,
    ):
        import chromadb
        from google import genai

        self.chunks = {c.chunk_id: c for c in chunks}
        self.embed_model = embed_model
        self._client = genai.Client(api_key=require_env("GEMINI_API_KEY"))
        self._collection = chromadb.PersistentClient(path=str(persist_dir)).get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    @property
    def size(self) -> int:
        return self._collection.count()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(model=self.embed_model, contents=texts)
        return [e.values for e in result.embeddings]

    def build_index(self, batch_size: int = 20, pause: float = 1.0, rebuild: bool = False) -> int:
        """Embed every chunk once. Skips work if the collection is already full."""
        if rebuild and self.size:
            self._collection.delete(ids=self._collection.get()["ids"])
        if self.size >= len(self.chunks):
            return self.size

        chunks = list(self.chunks.values())
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            self._collection.upsert(
                ids=[c.chunk_id for c in batch],
                embeddings=self._embed([c.text for c in batch]),
                documents=[c.text for c in batch],
                metadatas=[{
                    "source": c.source,
                    "section": c.section,
                    "content_type": c.content_type,
                    "page": c.page,
                    "token_count": c.token_count,
                } for c in batch],
            )
            time.sleep(pause)  # stay inside the free-tier rate limit
        return self.size

    def retrieve(self, query: str, k: int = SETTINGS.top_k) -> list[RetrievedChunk]:
        if not self.size:
            raise RuntimeError("The vector index is empty. Run `python -m parishiksha index` first.")
        result = self._collection.query(
            query_embeddings=self._embed([query]), n_results=k, include=["distances"]
        )
        return [
            # Chroma returns cosine *distance*; similarity = 1 - distance
            RetrievedChunk(self.chunks[chunk_id], round(1 - distance, 4))
            for chunk_id, distance in zip(result["ids"][0], result["distances"][0])
            if chunk_id in self.chunks
        ]
