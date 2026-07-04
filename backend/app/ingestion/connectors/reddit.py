from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

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
                except httpx.HTTPError:
                    continue

        return normalized

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
