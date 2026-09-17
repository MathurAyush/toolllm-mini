from __future__ import annotations

from apis.base import BaseAPI

from .embedder import TfidfEmbedder
from .types import RetrievedAPI


class APIRetriever:
    """Ranks registered APIs by relevance to a natural language instruction
    using a pluggable text embedder. Defaults to TF-IDF; pass an
    `embedder` implementing `fit(corpus)` / `similarity(query)` (such as
    `SentenceTransformerEmbedder`) to rank by semantic similarity instead.
    """

    def __init__(self, apis: list[BaseAPI], embedder=None) -> None:
        self._apis = apis
        self._embedder = embedder if embedder is not None else TfidfEmbedder()
        corpus = [f"{api.name} {api.description}" for api in apis]
        self._embedder.fit(corpus)

    def retrieve(self, instruction: str, top_k: int = 3) -> list[RetrievedAPI]:
        scores = self._embedder.similarity(instruction)
        ranked = sorted(zip(self._apis, scores), key=lambda pair: pair[1], reverse=True)
        return [RetrievedAPI(api=api, score=float(score)) for api, score in ranked[:top_k]]
