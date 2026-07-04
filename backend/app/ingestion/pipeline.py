from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.db.chroma_client import ChromaReviewStore
from app.ingestion.connectors.app_store import AppStoreConnector
from app.ingestion.connectors.base import RawReview
from app.ingestion.connectors.play_store import PlayStoreConnector
from app.ingestion.connectors.reddit import RedditConnector
from app.ingestion.normalizer import (
    load_sample_reviews,
    process_reviews,
    save_raw_reviews,
)


class IngestionPipeline:
    def __init__(self, settings: Settings | None = None, store: ChromaReviewStore | None = None):
        self.settings = settings or get_settings()
        self.store = store or ChromaReviewStore(self.settings)
        self.play_store = PlayStoreConnector(self.settings)
        self.app_store = AppStoreConnector(self.settings)
        self.reddit = RedditConnector(self.settings)
        self._last_ingestion_at: datetime | None = None

    @property
    def last_ingestion_at(self) -> datetime | None:
        return self._last_ingestion_at

    def run(
        self,
        count: int | None = None,
        use_sample: bool = False,
        sources: list[str] | None = None,
    ) -> dict:
        if use_sample:
            sample_path = self.settings.raw_data_path / "sample_reviews.json"
            raw_reviews = load_sample_reviews(sample_path, self.settings.play_store_app_name)
            source_label = "sample"
        else:
            active_sources = sources or ["play_store", "app_store", "reddit"]
            raw_reviews = self._fetch_all(count=count, sources=active_sources)
            source_label = "+".join(active_sources)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            save_raw_reviews(
                raw_reviews,
                self.settings.raw_data_path / f"all_sources_{timestamp}.json",
            )

        chunks = process_reviews(raw_reviews)
        if not chunks:
            return {
                "ingested": 0,
                "source": source_label,
                "message": "No reviews found to ingest.",
            }

        processed_path = self.settings.processed_data_path / f"{source_label}_latest.json"
        processed_path.parent.mkdir(parents=True, exist_ok=True)
        processed_path.write_text(
            json.dumps(
                [{"id": chunk.doc_id, "text": chunk.text, "metadata": chunk.metadata} for chunk in chunks],
                indent=2,
            ),
            encoding="utf-8",
        )

        ingested = self.store.upsert_documents(
            ids=[chunk.doc_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )
        self._last_ingestion_at = datetime.now(timezone.utc)

        by_source = self.store.count_by_source()
        return {
            "ingested": ingested,
            "source": source_label,
            "by_source": by_source,
            "message": f"Successfully ingested {ingested} review chunks from {source_label}.",
        }

    def _fetch_all(self, count: int | None, sources: list[str]) -> list[RawReview]:
        all_reviews: list[RawReview] = []
        errors: list[str] = []

        connectors = {
            "play_store": self.play_store,
            "app_store": self.app_store,
            "reddit": self.reddit,
        }

        for source in sources:
            connector = connectors.get(source)
            if connector is None:
                continue
            try:
                reviews = connector.fetch(count=count)
                all_reviews.extend(reviews)
            except Exception as exc:
                errors.append(f"{source}: {exc}")

        if not all_reviews and errors:
            raise RuntimeError("All sources failed: " + "; ".join(errors))

        return all_reviews
