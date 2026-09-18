"""Ask the agent a single question from the command line.

Usage:
    python scripts/ask.py "What's the weather in Tokyo?"
    python scripts/ask.py --dfsdt "Convert 20 USD to EUR and define 'serendipity'"

Uses the same provider/model selection as run_benchmark.py
(BENCHMARK_PROVIDER, BENCHMARK_MODEL, loaded from a local .env file).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

from agent.dfsdt import DFSDTAgent
from agent.llm import BaseLLM
from agent.react import ReActAgent
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction", help="Natural language question or task for the agent.")
    parser.add_argument(
        "--dfsdt", action="store_true", help="Use the DFSDT search agent instead of plain ReAct."
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of candidate APIs to retrieve (default: 5)."
    )
    args = parser.parse_args()

    registry = keyless_registry()
    retriever = APIRetriever(apis=registry.all())
    candidate_apis = [r.api for r in retriever.retrieve(args.instruction, top_k=args.top_k)]

    llm = _build_llm()
    agent = DFSDTAgent(registry=registry, llm=llm) if args.dfsdt else ReActAgent(registry=registry, llm=llm)

    result = agent.run(args.instruction, candidate_apis=candidate_apis)

    answer = result.answer or "(agent did not produce a final answer)"
    sys.stdout.buffer.write(answer.encode("utf-8", errors="replace") + b"\n")


if __name__ == "__main__":
    main()
