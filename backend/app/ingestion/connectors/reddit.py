from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import Settings, get_settings
from app.ingestion.connectors.base import RawReview


class RedditConnector:
    source = "reddit"
    API_BASE = "https://api.pullpush.io/reddit"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def fetch(self, count: int | None = None) -> list[RawReview]:
        limit_per_sub = count or self.settings.reddit_post_limit
        normalized: list[RawReview] = []
        api_failed = False

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            for subreddit in self.settings.reddit_subreddits:
                try:
                    posts = self._fetch_submissions(client, subreddit, limit_per_sub)
                    for post in posts:
                        normalized.append(post)
                        if self.settings.reddit_include_comments:
                            comments = self._fetch_comments(client, post)
                            normalized.extend(comments)
                    time.sleep(2)
                except httpx.HTTPError as exc:
                    print(f"Reddit API fetch failed for r/{subreddit}: {exc}")
                    api_failed = True
                    continue

        if not normalized or api_failed:
            print("Reddit API fetch failed or returned no posts. Attempting fallback to local cache...")
            normalized = self._fetch_from_local_cache()
            print(f"Loaded {len(normalized)} Reddit reviews from local cache.")

        return normalized

    def _fetch_from_local_cache(self) -> list[RawReview]:
        raw_path = Path(self.settings.raw_data_path)
        if not raw_path.exists():
            return []

        # Find all all_sources_*.json files
        cached_files = sorted(raw_path.glob("all_sources_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for cached_file in cached_files:
            try:
                with open(cached_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    continue

                cached_reviews = []
                for item in data:
                    if item.get("source") == "reddit":
                        cached_reviews.append(
                            RawReview(
                                native_id=item["native_id"],
                                source="reddit",
                                text=item["text"],
                                title=item.get("title"),
                                rating=item.get("rating"),
                                author=item.get("author", "anonymous"),
                                created_at=datetime.fromisoformat(item["created_at"]),
                                url=item.get("url", ""),
                                app_name=item.get("app_name", "Spotify"),
                                locale=item.get("locale"),
                            )
                        )
                if cached_reviews:
                    return cached_reviews
            except Exception as exc:
                print(f"Error loading cached file {cached_file}: {exc}")
        return []

    def _fetch_submissions(
        self, client: httpx.Client, subreddit: str, limit: int
    ) -> list[RawReview]:
        params = {
            "subreddit": subreddit,
            "q": self.settings.reddit_search_query,
            "size": min(limit, 100),
            "sort": "desc",
            "sort_type": "score",
        }
        response = client.get(f"{self.API_BASE}/search/submission/", params=params)
        response.raise_for_status()
        data = response.json()

        posts: list[RawReview] = []
        for item in data.get("data", []):
            post_id = item.get("id")
            if not post_id:
                continue

            title = (item.get("title") or "").strip()
            body = (item.get("selftext") or "").strip()
            text = f"{title}\n\n{body}".strip() if body else title
            if not text:
                continue

            created_raw = item.get("created_utc", 0)
            created_at = datetime.fromtimestamp(float(created_raw), tz=timezone.utc)
            permalink = item.get("permalink", "")
            full_url = f"https://www.reddit.com{permalink}" if permalink else item.get("url", "")

            posts.append(
                RawReview(
                    native_id=str(post_id),
                    source="reddit",
                    text=text,
                    title=title,
                    rating=None,
                    author=self._anonymize(item.get("author") or "anonymous"),
                    created_at=created_at,
                    url=full_url,
                    app_name=self.settings.play_store_app_name,
                    locale="en",
                )
            )
        return posts

    def _fetch_comments(self, client: httpx.Client, post: RawReview) -> list[RawReview]:
        params = {
            "link_id": f"t3_{post.native_id}",
            "size": self.settings.reddit_comment_limit,
            "sort": "desc",
            "sort_type": "score",
        }
        try:
            response = client.get(f"{self.API_BASE}/search/comment/", params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return []

        comments: list[RawReview] = []
        for item in data.get("data", []):
            body = (item.get("body") or "").strip()
            if not body or body in ("[deleted]", "[removed]"):
                continue

            comment_id = item.get("id")
            if not comment_id:
                continue

            created_raw = item.get("created_utc", 0)
            created_at = datetime.fromtimestamp(float(created_raw), tz=timezone.utc)
            permalink = item.get("permalink", "")
            full_url = f"https://www.reddit.com{permalink}" if permalink else post.url

            comments.append(
                RawReview(
                    native_id=f"{post.native_id}_{comment_id}",
                    source="reddit",
                    text=body,
                    title=f"Comment on: {post.title}",
                    rating=None,
                    author=self._anonymize(item.get("author") or "anonymous"),
                    created_at=created_at,
                    url=full_url,
                    app_name=post.app_name,
                    locale="en",
                )
            )
        return comments

    @staticmethod
    def _anonymize(name: str) -> str:
        digest = hashlib.sha256(name.encode()).hexdigest()[:8]
        return f"user_{digest}"
