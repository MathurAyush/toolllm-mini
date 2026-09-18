"""Ask the DFSDT agent a single question from the command line.

Usage:
    python ask.py "What's the weather in Tokyo?"

Uses the same provider/model selection as scripts/run_benchmark.py
(BENCHMARK_PROVIDER, BENCHMARK_MODEL, loaded from a local .env file).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.dfsdt import DFSDTAgent
from agent.llm import BaseLLM
from apis.registry import keyless_registry
from retriever.retriever import APIRetriever


def _build_llm() -> BaseLLM:
    provider = os.environ.get("BENCHMARK_PROVIDER", "gemini")
    if provider == "anthropic":
        from agent.anthropic_llm import AnthropicLLM

        return AnthropicLLM(model=os.environ.get("BENCHMARK_MODEL", "claude-haiku-4-5-20251001"))
    if provider == "gemini":
        from agent.gemini_llm import GeminiLLM

        return GeminiLLM(model=os.environ.get("BENCHMARK_MODEL", "gemini-3.5-flash-lite"))
    raise ValueError(f"Unknown BENCHMARK_PROVIDER '{provider}' (expected 'anthropic' or 'gemini').")


def main() -> None:
    if len(sys.argv) != 2:
        print('Usage: python ask.py "your question here"', file=sys.stderr)
        sys.exit(1)
    instruction = sys.argv[1]

    registry = keyless_registry()
    retriever = APIRetriever(apis=registry.all())
    candidate_apis = [r.api for r in retriever.retrieve(instruction, top_k=5)]

    agent = DFSDTAgent(registry=registry, llm=_build_llm())
    result = agent.run(instruction, candidate_apis=candidate_apis)

    answer = result.answer or "(agent did not produce a final answer)"
    sys.stdout.buffer.write(answer.encode("utf-8", errors="replace") + b"\n")


if __name__ == "__main__":
    main()
