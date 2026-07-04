from fastapi import APIRouter, Depends, HTTPException

from app.db.chroma_client import ChromaReviewStore
from app.ingestion.pipeline import IngestionPipeline
from app.models.schemas import IngestStatusResponse, IngestTriggerRequest

router = APIRouter(prefix="/ingest", tags=["ingest"])


def get_pipeline() -> IngestionPipeline:
    from app.main import ingestion_pipeline

    return ingestion_pipeline


def get_store() -> ChromaReviewStore:
    from app.main import review_store

    return review_store


@router.post("/trigger")
async def trigger_ingestion(
    payload: IngestTriggerRequest,
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> dict:
    try:
        result = pipeline.run(
            count=payload.count,
            use_sample=payload.use_sample,
            sources=payload.sources,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/status", response_model=IngestStatusResponse)
async def ingestion_status(
    pipeline: IngestionPipeline = Depends(get_pipeline),
    store: ChromaReviewStore = Depends(get_store),
) -> IngestStatusResponse:
    total = store.get_document_count()
    sources = store.count_by_source()
    status = "ready" if total > 0 else "empty"
    return IngestStatusResponse(
        status=status,
        total_documents=total,
        sources=sources,
        last_ingestion_at=pipeline.last_ingestion_at,
        message="Ingestion pipeline is ready." if total > 0 else "No documents indexed yet.",
    )
