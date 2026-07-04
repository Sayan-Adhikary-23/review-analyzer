from __future__ import annotations

from app.config import Settings, get_settings
from app.db.chroma_client import ChromaReviewStore
from app.models.schemas import Citation, QueryFilters


class Retriever:
    def __init__(self, settings: Settings | None = None, store: ChromaReviewStore | None = None):
        self.settings = settings or get_settings()
        self.store = store or ChromaReviewStore(self.settings)

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        filters: QueryFilters | None = None,
    ) -> list[Citation]:
        k = top_k or self.settings.default_top_k
        where = self._build_where_clause(filters)
        results = self.store.query(question, top_k=k, where=where)

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        citations: list[Citation] = []
        for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            relevance = max(0.0, 1.0 - float(distance))
            if relevance < self.settings.similarity_threshold:
                continue

            rating = metadata.get("rating", -1)
            citations.append(
                Citation(
                    id=doc_id,
                    excerpt=document[:500],
                    source=metadata.get("source", "play_store"),
                    rating=rating if rating >= 1 else None,
                    url=metadata.get("url") or None,
                    created_at=metadata.get("created_at"),
                    relevance_score=round(relevance, 3),
                )
            )

        if not citations and ids:
            doc_id, document, metadata, distance = ids[0], documents[0], metadatas[0], distances[0]
            rating = metadata.get("rating", -1)
            citations.append(
                Citation(
                    id=doc_id,
                    excerpt=document[:500],
                    source=metadata.get("source", "play_store"),
                    rating=rating if rating >= 1 else None,
                    url=metadata.get("url") or None,
                    created_at=metadata.get("created_at"),
                    relevance_score=round(max(0.0, 1.0 - float(distance)), 3),
                )
            )

        return citations

    def _build_where_clause(self, filters: QueryFilters | None) -> dict | None:
        if not filters:
            return None

        clauses: list[dict] = []
        if filters.sources:
            if len(filters.sources) == 1:
                clauses.append({"source": filters.sources[0]})
            else:
                clauses.append({"source": {"$in": filters.sources}})
        if filters.app_name:
            clauses.append({"app_name": filters.app_name})
        if filters.min_rating is not None:
            clauses.append({"rating": {"$gte": filters.min_rating}})
        if filters.max_rating is not None:
            clauses.append({"rating": {"$lte": filters.max_rating}})

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
