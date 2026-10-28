"""Generates data/benchmark.jsonl: LLM-written tasks over the keyless tool
pool, filtered and verified against real tool calls.

Usage:
    python scripts/generate_benchmark.py [--per-difficulty 22] [--seed 0]

Samples 1-3 related tools per round, asks the model for instructions that
need them, drops duplicates, instructions naming nonexistent tools and
tasks whose reference plan does not run, then labels the rest easy (1
tool), medium (2 independent tools) or hard (3 tools, or a call that uses
an earlier call's output). Live-data tasks store a tolerance check against
a fresh run of the reference plan instead of a fixed value. The tool
groups and the dev/test split come from --seed.

Requires an API key for the configured provider (ANTHROPIC_API_KEY or
GEMINI_API_KEY), loaded from a local .env file if present, and network
access for the tool calls. Select the provider with BENCHMARK_PROVIDER
("anthropic" or "gemini", default "gemini") and override the model with
BENCHMARK_MODEL.
"""

from __future__ import annotations

import argparse
import datetime
import os
import random
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

from agent.llm import BaseLLM
from apis.registry import keyless_registry
from eval.benchmark_generator import DIFFICULTIES, generate_benchmark, write_jsonl

_OUTPUT_PATH = _ROOT / "data" / "benchmark.jsonl"
_PROVIDER = os.environ.get("BENCHMARK_PROVIDER", "gemini")


def _build_llm() -> BaseLLM:
    if _PROVIDER == "anthropic":
        from agent.anthropic_llm import AnthropicLLM

        return AnthropicLLM(model=os.environ.get("BENCHMARK_MODEL", "claude-haiku-4-5-20251001"), max_tokens=4096)
    if _PROVIDER == "gemini":
        from agent.gemini_llm import GeminiLLM

        return GeminiLLM(model=os.environ.get("BENCHMARK_MODEL", "gemini-3.5-flash-lite"))
    raise ValueError(f"Unknown BENCHMARK_PROVIDER '{_PROVIDER}' (expected 'anthropic' or 'gemini').")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-difficulty", type=int, default=22, help="tasks to keep per difficulty")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-rounds", type=int, default=80, help="model calls before giving up")
    parser.add_argument("--samples", type=int, default=10, help="sample tasks to print")
    parser.add_argument("--output", type=Path, default=_OUTPUT_PATH)
    parser.add_argument("--quiet", action="store_true", help="hide per-candidate progress")
    args = parser.parse_args()

    tasks, stats = generate_benchmark(
        _build_llm(),
        keyless_registry(),
        per_difficulty=args.per_difficulty,
        seed=args.seed,
        max_rounds=args.max_rounds,
        today=datetime.date.today().isoformat(),
        log=(lambda _: None) if args.quiet else print,
    )
    args.output.parent.mkdir(exist_ok=True)
    write_jsonl(tasks, args.output)

    print(f"\nWrote {len(tasks)} tasks to {args.output}")
    print(f"{stats.llm_calls} model calls, {stats.candidates} candidates, {sum(stats.rejected.values())} rejected")
    for reason, count in stats.rejected.most_common():
        print(f"  {count:4d}  {reason}")

    by_difficulty = Counter(task["difficulty"] for task in tasks)
    by_split = Counter((task["difficulty"], task["split"]) for task in tasks)
    print("\nTasks per difficulty:")
    for difficulty in DIFFICULTIES:
        print(
            f"  {difficulty:<7} {by_difficulty[difficulty]:3d}"
            f"  (dev {by_split[difficulty, 'dev']}, test {by_split[difficulty, 'test']})"
        )

    print(f"\n{args.samples} sample tasks:")
    for task in random.Random(args.seed).sample(tasks, min(args.samples, len(tasks))):
        check = task.get("expected_facts") or task["expected_value"]["check"]
        print(f"  [{task['id']} {task['difficulty']}] {task['instruction']}")
        print(f"      tools: {', '.join(task['expected_tools'])} | expect: {check}")


if __name__ == "__main__":
    main()
