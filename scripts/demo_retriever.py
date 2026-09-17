"""Quick demo comparing the semantic (sentence-transformers) retriever
against the keyword-match baseline on the sample instructions.

Usage:
    python scripts/demo_retriever.py

Requires `sentence-transformers` to be installed (see requirements.txt);
the first run downloads the small pretrained model.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apis.registry import full_registry
from retriever.keyword_baseline import KeywordMatchRetriever
from retriever.retriever import APIRetriever
from retriever.semantic_embedder import SentenceTransformerEmbedder

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_instructions.json"
)


def main() -> None:
    apis = full_registry().all()

    keyword_retriever = KeywordMatchRetriever(apis)
    semantic_retriever = APIRetriever(apis, embedder=SentenceTransformerEmbedder())

    with open(_DATA_PATH, encoding="utf-8") as f:
        samples = json.load(f)

    for sample in samples:
        instruction = sample["instruction"]
        print(f"\nInstruction: {instruction}")

        print("  Keyword-match baseline:")
        for result in keyword_retriever.retrieve(instruction, top_k=2):
            print(f"    {result.api.name:<20} score={result.score:.3f}")

        print("  Semantic (sentence-transformers):")
        for result in semantic_retriever.retrieve(instruction, top_k=2):
            print(f"    {result.api.name:<20} score={result.score:.3f}")


if __name__ == "__main__":
    main()
