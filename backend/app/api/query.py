from fastapi import APIRouter, Depends

from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag_orchestrator import RagOrchestrator

router = APIRouter(prefix="/query", tags=["query"])


def get_orchestrator() -> RagOrchestrator:
    from app.main import orchestrator

    return orchestrator


@router.post("", response_model=QueryResponse)
async def query_reviews(
    payload: QueryRequest,
    orchestrator: RagOrchestrator = Depends(get_orchestrator),
) -> QueryResponse:
    return await orchestrator.query(
        question=payload.question,
        filters=payload.filters,
        options=payload.options,
    )
