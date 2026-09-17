from __future__ import annotations

from dataclasses import dataclass

from apis.base import BaseAPI

from .embedder import TfidfEmbedder


@dataclass
class RetrievedAPI:
    api: BaseAPI
    score: float


class APIRetriever:
    """Ranks registered APIs by relevance to a natural language instruction."""

    def __init__(self, apis: list[BaseAPI]) -> None:
        self._apis = apis
        self._embedder = TfidfEmbedder()
        corpus = [f"{api.name} {api.description}" for api in apis]
        self._embedder.fit(corpus)

    def retrieve(self, instruction: str, top_k: int = 3) -> list[RetrievedAPI]:
        scores = self._embedder.similarity(instruction)
        ranked = sorted(zip(self._apis, scores), key=lambda pair: pair[1], reverse=True)
        return [RetrievedAPI(api=api, score=float(score)) for api, score in ranked[:top_k]]
