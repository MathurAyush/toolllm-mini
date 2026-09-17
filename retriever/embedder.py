from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfEmbedder:
    """Minimal TF-IDF based text embedder used to rank API descriptions
    against a natural language instruction."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer()
        self._matrix = None
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._fitted = True

    def similarity(self, query: str) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Embedder must be fit before computing similarity.")
        query_vec = self._vectorizer.transform([query])
        return cosine_similarity(query_vec, self._matrix)[0]
