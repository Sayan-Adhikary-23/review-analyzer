from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import Settings, get_settings


class Embedder:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
