from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.ingestion.connectors.base import RawReview


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def dedupe_reviews(reviews: list[RawReview]) -> list[RawReview]:
    seen: set[str] = set()
    unique: list[RawReview] = []
    for review in reviews:
        key = f"{review.source}:{review.native_id}"
        if key in seen or not review.text:
            continue
        seen.add(key)
        unique.append(review)
    return unique


def estimate_sentiment(text: str, rating: int | None) -> float:
    negative_words = {"bad", "terrible", "awful", "hate", "broken", "bug", "crash", "slow", "worst"}
    positive_words = {"love", "great", "awesome", "excellent", "amazing", "perfect", "best", "helpful"}
    tokens = set(re.findall(r"[a-z']+", text.lower()))
    score = 0.0
    score += len(tokens & positive_words) * 0.15
    score -= len(tokens & negative_words) * 0.15
    if rating is not None:
        score += (rating - 3) * 0.25
    return max(-1.0, min(1.0, score))


def infer_segments(text: str, rating: int | None, sentiment: float) -> list[str]:
    lowered = text.lower()
    segments: list[str] = []
    if any(word in lowered for word in ("discover", "recommendation", "new music", "find music")):
        segments.append("discovery-focused")
    if any(word in lowered for word in ("same song", "repeat", "replay", "comfort")):
        segments.append("repeat-listening")
    if len(text.split()) > 80:
        segments.append("power-user")
    if rating is not None and rating <= 2 and sentiment < 0:
        segments.append("frustrated-user")
    return segments


@dataclass
class ProcessedChunk:
    doc_id: str
    text: str
    metadata: dict


def build_document_id(source: str, native_id: str, chunk_index: int) -> str:
    return f"{source}:{native_id}_{chunk_index}"


def process_reviews(reviews: list[RawReview]) -> list[ProcessedChunk]:
    cleaned = dedupe_reviews(reviews)
    chunks: list[ProcessedChunk] = []

    for review in cleaned:
        text = clean_text(review.text)
        if not text:
            continue

        sentiment = estimate_sentiment(text, review.rating)
        segments = infer_segments(text, review.rating, sentiment)
        parent_id = f"{review.source}:{review.native_id}"
        doc_id = build_document_id(review.source, review.native_id, 0)

        metadata = {
            "source": review.source,
            "app_name": review.app_name,
            "rating": review.rating if review.rating is not None else -1,
            "title": review.title or "",
            "author": review.author,
            "created_at": review.created_at.isoformat(),
            "url": review.url,
            "language": "en",
            "sentiment": float(sentiment),
            "segments": json.dumps(segments),
            "chunk_index": 0,
            "parent_id": parent_id,
        }
        chunks.append(ProcessedChunk(doc_id=doc_id, text=text, metadata=metadata))

    return chunks


def save_raw_reviews(reviews: list[RawReview], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "native_id": review.native_id,
            "source": review.source,
            "text": review.text,
            "title": review.title,
            "rating": review.rating,
            "author": review.author,
            "created_at": review.created_at.isoformat(),
            "url": review.url,
            "app_name": review.app_name,
            "locale": review.locale,
        }
        for review in reviews
    ]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_sample_reviews(sample_path: Path, app_name: str = "Spotify") -> list[RawReview]:
    if not sample_path.exists():
        return []

    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    reviews: list[RawReview] = []
    for item in payload:
        reviews.append(
            RawReview(
                native_id=item["native_id"],
                source=item.get("source", "play_store"),
                text=item["text"],
                title=item.get("title"),
                rating=item.get("rating"),
                author=item.get("author", "anonymous"),
                created_at=datetime.fromisoformat(item["created_at"]),
                url=item.get("url", ""),
                app_name=item.get("app_name", app_name),
                locale=item.get("locale"),
            )
        )
    return reviews
