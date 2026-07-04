from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.db.chroma_client import ChromaReviewStore
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


def get_store() -> ChromaReviewStore:
    from app.main import review_store

    return review_store


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    store: ChromaReviewStore = Depends(get_store),
) -> HealthResponse:
    try:
        count = store.get_document_count()
        chroma_status = "ok"
    except Exception:
        count = 0
        chroma_status = "error"

    return HealthResponse(
        status="ok" if chroma_status == "ok" else "degraded",
        chroma=chroma_status,
        openai_configured=bool(settings.openai_api_key.strip()),
        document_count=count,
    )
