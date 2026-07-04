from __future__ import annotations

import logging
import time

from app.config import Settings, get_settings
from app.models.schemas import QueryFilters, QueryMetadata, QueryOptions, QueryResponse
from app.services.openai_client import OpenAIClient
from app.services.prompt_builder import build_messages, build_retrieval_fallback
from app.services.retriever import Retriever

logger = logging.getLogger(__name__)

class RagOrchestrator:
    def __init__(
        self,
        settings: Settings | None = None,
        retriever: Retriever | None = None,
        openai_client: OpenAIClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.retriever = retriever or Retriever(self.settings)
        self.openai_client = openai_client or OpenAIClient(self.settings)

    async def query(
        self,
        question: str,
        filters: QueryFilters | None = None,
        options: QueryOptions | None = None,
    ) -> QueryResponse:
        start = time.perf_counter()
        options = options or QueryOptions()
        citations = self.retriever.retrieve(
            question=question,
            top_k=options.top_k,
            filters=filters,
        )

        openai_available = self.openai_client.is_configured
        openai_error: str | None = None
        if openai_available:
            try:
                messages = build_messages(question, citations)
                answer = await self.openai_client.generate(messages)
            except Exception as exc:
                openai_available = False
                openai_error = str(exc)
                logger.warning("OpenAI request failed: %s", exc)
                answer = build_retrieval_fallback(question, citations, reason=openai_error)
        else:
            answer = build_retrieval_fallback(question, citations)

        latency_ms = int((time.perf_counter() - start) * 1000)
        sources_used = sorted({citation.source for citation in citations})

        return QueryResponse(
            answer=answer,
            citations=citations,
            metadata=QueryMetadata(
                retrieved_count=len(citations),
                sources_used=sources_used,
                model=self.settings.openai_model if openai_available else "retrieval-only",
                latency_ms=latency_ms,
                openai_available=openai_available,
            ),
        )
