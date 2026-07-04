from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx

from app.config import Settings, get_settings
from app.ingestion.connectors.base import RawReview


class AppStoreConnector:
    source = "app_store"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def fetch(self, count: int | None = None) -> list[RawReview]:
        limit = count or self.settings.app_store_review_count
        normalized: list[RawReview] = []
        pages_needed = min(10, (limit // 50) + 1)

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            for page in range(1, pages_needed + 1):
                if len(normalized) >= limit:
                    break
                page_reviews = self._fetch_page(client, page)
                normalized.extend(page_reviews)

        return normalized[:limit]

    def _fetch_page(self, client: httpx.Client, page: int) -> list[RawReview]:
        url = (
            f"https://itunes.apple.com/{self.settings.app_store_country}/rss/customerreviews/"
            f"page={page}/id={self.settings.app_store_app_id}/sortby=mostrecent/json"
        )
        response = client.get(url)
        response.raise_for_status()
        data = response.json()

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            return []

        # First entry on page 1 is app metadata, not a review
        if page == 1 and entries and "im:rating" not in entries[0]:
            entries = entries[1:]

        reviews: list[RawReview] = []
        for entry in entries:
            rating_raw = entry.get("im:rating", {}).get("label")
            title = entry.get("title", {}).get("label", "")
            text = entry.get("content", {}).get("label", "")
            if isinstance(text, dict):
                text = text.get("label", "")
            text = (text or "").strip()
            if not text:
                continue

            author = entry.get("author", {}).get("name", {}).get("label", "anonymous")
            review_id = entry.get("id", {}).get("label", "")
            if not review_id:
                review_id = hashlib.sha256(f"{author}{text}".encode()).hexdigest()[:16]

            updated = entry.get("updated", {}).get("label")
            try:
                created_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)

            reviews.append(
                RawReview(
                    native_id=str(review_id),
                    source="app_store",
                    text=text,
                    title=title if title != text else None,
                    rating=int(rating_raw) if rating_raw else None,
                    author=self._anonymize(author),
                    created_at=created_at,
                    url=f"https://apps.apple.com/app/id{self.settings.app_store_app_id}",
                    app_name=self.settings.app_store_app_name,
                    locale=self.settings.app_store_country,
                )
            )
        return reviews

    @staticmethod
    def _anonymize(name: str) -> str:
        digest = hashlib.sha256(name.encode()).hexdigest()[:8]
        return f"user_{digest}"
