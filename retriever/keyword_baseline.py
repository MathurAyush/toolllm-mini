from __future__ import annotations

import re

from apis.base import BaseAPI

from .types import RetrievedAPI

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


class KeywordMatchRetriever:
    """Baseline retriever with no learned embeddings: ranks APIs by the
    Jaccard overlap between the instruction's tokens and each API's name
    plus description tokens. Useful as a lower bound to compare the
    TF-IDF and semantic retrievers against.
    """

    def __init__(self, apis: list[BaseAPI]) -> None:
        self._apis = apis
        self._doc_tokens = [_tokenize(f"{api.name} {api.description}") for api in apis]

    def retrieve(self, instruction: str, top_k: int = 3) -> list[RetrievedAPI]:
        query_tokens = _tokenize(instruction)
        scored = []
        for api, tokens in zip(self._apis, self._doc_tokens):
            union = query_tokens | tokens
            score = len(query_tokens & tokens) / len(union) if union else 0.0
            scored.append((api, score))
        ranked = sorted(scored, key=lambda pair: pair[1], reverse=True)
        return [RetrievedAPI(api=api, score=score) for api, score in ranked[:top_k]]
