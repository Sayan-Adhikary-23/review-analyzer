from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.query import router as query_router
from app.config import get_settings
from app.db.chroma_client import ChromaReviewStore
from app.ingestion.pipeline import IngestionPipeline
from app.services.openai_client import OpenAIClient
from app.services.rag_orchestrator import RagOrchestrator
from app.services.retriever import Retriever

settings = get_settings()
review_store = ChromaReviewStore(settings)
ingestion_pipeline = IngestionPipeline(settings, review_store)
retriever = Retriever(settings, review_store)
orchestrator = RagOrchestrator(settings, retriever, OpenAIClient(settings))

app = FastAPI(
    title="Review Discovery Engine",
    description="RAG-powered review analysis for App Store, Play Store, and Reddit feedback.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")
