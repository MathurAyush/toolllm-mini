from __future__ import annotations

import numpy as np


class SentenceTransformerEmbedder:
    """Embeds text with a pretrained sentence-transformers model and ranks
    by cosine similarity between normalized embeddings.

    The `sentence-transformers` import is deferred to instantiation so
    that modules importing this class don't require the (heavy) library
    unless an instance is actually created.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._corpus_embeddings: np.ndarray | None = None
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._corpus_embeddings = self._model.encode(corpus, normalize_embeddings=True)
        self._fitted = True

    def similarity(self, query: str) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Embedder must be fit before computing similarity.")
        query_embedding = self._model.encode([query], normalize_embeddings=True)[0]
        return self._corpus_embeddings @ query_embedding
