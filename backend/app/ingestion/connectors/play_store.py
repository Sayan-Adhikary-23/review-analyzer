from __future__ import annotations

import hashlib
from datetime import datetime

from google_play_scraper import Sort, reviews

from app.config import Settings, get_settings
from app.ingestion.connectors.base import RawReview


class PlayStoreConnector:
    source = "play_store"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def fetch(self, count: int | None = None) -> list[RawReview]:
        limit = count or self.settings.play_store_review_count
        result, _ = reviews(
            self.settings.play_store_app_id,
            lang=self.settings.play_store_lang,
            country=self.settings.play_store_country,
            sort=Sort.NEWEST,
            count=limit,
        )

        normalized: list[RawReview] = []
        for item in result:
            review_id = item.get("reviewId") or hashlib.sha256(
                f"{item.get('userName', '')}{item.get('content', '')}{item.get('at', '')}".encode()
            ).hexdigest()[:16]

            created_at = item.get("at")
            if not isinstance(created_at, datetime):
                created_at = datetime.utcnow()

            normalized.append(
                RawReview(
                    native_id=str(review_id),
                    source="play_store",
                    text=(item.get("content") or "").strip(),
                    title=None,
                    rating=item.get("score"),
                    author=self._anonymize(item.get("userName") or "anonymous"),
                    created_at=created_at,
                    url=f"https://play.google.com/store/apps/details?id={self.settings.play_store_app_id}&reviewId={review_id}",
                    app_name=self.settings.play_store_app_name,
                    locale=self.settings.play_store_country,
                )
            )
        return normalized

    @staticmethod
    def _anonymize(name: str) -> str:
        digest = hashlib.sha256(name.encode()).hexdigest()[:8]
        return f"user_{digest}"
