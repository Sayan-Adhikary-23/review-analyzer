import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "backend" / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 1024

    chroma_path: Path = PROJECT_ROOT / "data" / "chroma"
    raw_data_path: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_path: Path = PROJECT_ROOT / "data" / "processed"

    collection_name: str = "reviews"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    default_top_k: int = 8
    similarity_threshold: float = 0.3

    play_store_app_id: str = "com.spotify.music"
    play_store_app_name: str = "Spotify"
    play_store_lang: str = "en"
    play_store_country: str = "us"
    play_store_review_count: int = 100

    app_store_app_id: str = "324684580"
    app_store_app_name: str = "Spotify"
    app_store_country: str = "us"
    app_store_review_count: int = 100

    reddit_subreddits: list[str] = ["spotify"]
    reddit_search_query: str = "discovery OR recommendation OR playlist"
    reddit_post_limit: int = 50
    reddit_comment_limit: int = 10
    reddit_include_comments: bool = True
    reddit_user_agent: str = "ReviewAnalyzer/1.0"

    cors_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
