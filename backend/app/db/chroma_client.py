from __future__ import annotations

import json
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import Settings, get_settings
from app.services.embedder import Embedder


class ChromaReviewStore:
    def __init__(self, settings: Settings | None = None, embedder: Embedder | None = None):
        self.settings = settings or get_settings()
        self.embedder = embedder or Embedder(self.settings)
        self._client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
        self._collection: Collection | None = None

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self.settings.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def upsert_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> int:
        embeddings = self.embedder.embed_documents(documents)
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def query(
        self,
        query_text: str,
        top_k: int = 8,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query_embedding = self.embedder.embed_query(query_text)
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def get_document_count(self) -> int:
        return self.collection.count()

    def count_by_source(self) -> dict[str, int]:
        result = self.collection.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for metadata in result.get("metadatas") or []:
            source = metadata.get("source", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts

    def get_by_id(self, doc_id: str) -> dict[str, Any] | None:
        result = self.collection.get(ids=[doc_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        metadata = result["metadatas"][0]
        segments_raw = metadata.get("segments", "[]")
        segments = json.loads(segments_raw) if isinstance(segments_raw, str) else segments_raw
        rating = metadata.get("rating", -1)
        return {
            "id": result["ids"][0],
            "document": result["documents"][0],
            "metadata": {**metadata, "segments": segments, "rating": rating if rating >= 1 else None},
        }
