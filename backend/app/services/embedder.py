from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings


class Embedder:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._st_model = None
        self._onnx_fn = None

    def _use_sentence_transformers(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def _embed_with_sentence_transformers(self, texts: list[str]) -> list[list[float]]:
        from sentence_transformers import SentenceTransformer

        if self._st_model is None:
            self._st_model = SentenceTransformer(self.settings.embedding_model)
        vectors = self._st_model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def _embed_with_onnx(self, texts: list[str]) -> list[list[float]]:
        from chromadb.utils import embedding_functions

        if self._onnx_fn is None:
            self._onnx_fn = embedding_functions.ONNXMiniLM_L6_V2()
        return self._onnx_fn(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._use_sentence_transformers():
            return self._embed_with_sentence_transformers(texts)
        return self._embed_with_onnx(texts)

    def embed_query(self, text: str) -> list[float]:
        if self._use_sentence_transformers():
            return self._embed_with_sentence_transformers([text])[0]
        return self._embed_with_onnx([text])[0]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
