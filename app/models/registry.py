from collections.abc import Callable
from typing import Any, Self

from config import CONTRIEVER_MODEL, EMBEDDING_MODEL, NLI_MODEL


class ModelRegistry:
    _instance: "ModelRegistry | None" = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: dict[str, Any] = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def _load(self, key: str, model_name: str, loader: Callable[[str], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = loader(model_name)
        return self._cache[key]

    def nli(self) -> Any:
        return self._load("nli", NLI_MODEL, self._load_nli)

    def embeddings(self) -> Any:
        return self._load("embeddings", EMBEDDING_MODEL, self._load_embeddings)

    def contriever(self) -> Any:
        return self._load("contriever", CONTRIEVER_MODEL, self._load_contriever)

    def _load_nli(self, model_name: str) -> Any:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(model_name)

    def _load_embeddings(self, model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(model_name)

    def _load_contriever(self, model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(model_name)

    def health_status(self) -> dict[str, bool]:
        return {
            "nli": "nli" in self._cache,
            "embeddings": "embeddings" in self._cache,
            "contriever": "contriever" in self._cache,
        }
