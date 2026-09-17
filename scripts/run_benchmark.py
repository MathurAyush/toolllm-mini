"""Runs ReActAgent and DFSDTAgent on data/benchmark_instructions.json,
grades each final answer with an LLM-as-judge, and writes a per-instruction
CSV, a comparison table, and a pass-rate bar chart to results/.

Usage:
    python scripts/run_benchmark.py

Requires ANTHROPIC_API_KEY, loaded from a local .env file if present.
Override the model with the BENCHMARK_MODEL environment variable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

from agent.anthropic_llm import AnthropicLLM
from agent.dfsdt import DFSDTAgent
from agent.react import ReActAgent
from apis.registry import keyless_registry
from eval.llm_judge import LLMJudge
from eval.report import write_benchmark_csv, write_comparison_table, write_pass_rate_bar_chart

_DATA_PATH = _ROOT / "data" / "benchmark_instructions.json"
_RESULTS_DIR = _ROOT / "results"
_MODEL = os.environ.get("BENCHMARK_MODEL", "claude-haiku-4-5-20251001")


def _run_and_judge(agent, instruction: str, apis: list, judge: LLMJudge) -> dict:
    result = agent.run(instruction, candidate_apis=apis)
    answer = result.answer or ""
    judged = judge.judge_pass(instruction, answer or "(agent did not produce a final answer)")
    return {
        "answer": answer,
        "steps": len(result.steps),
        "verdict": judged.verdict.value,
        "rationale": judged.rationale,
    }


def main() -> None:
    with open(_DATA_PATH, encoding="utf-8") as f:
        instructions = json.load(f)

    registry = keyless_registry()
    apis = registry.all()

    react_agent = ReActAgent(registry=registry, llm=AnthropicLLM(model=_MODEL))
    dfsdt_agent = DFSDTAgent(registry=registry, llm=AnthropicLLM(model=_MODEL))
    judge = LLMJudge(llm=AnthropicLLM(model=_MODEL))

    rows = []
    for item in instructions:
        instruction = item["instruction"]
        print(f"Running: {instruction}")

        react = _run_and_judge(react_agent, instruction, apis, judge)
        dfsdt = _run_and_judge(dfsdt_agent, instruction, apis, judge)

        rows.append(
            {
                "id": item["id"],
                "instruction": instruction,
                "complexity": item["complexity"],
                "expected_apis": ";".join(item["expected_apis"]),
                "react_answer": react["answer"],
                "react_steps": react["steps"],
                "react_verdict": react["verdict"],
                "react_rationale": react["rationale"],
                "dfsdt_answer": dfsdt["answer"],
                "dfsdt_steps": dfsdt["steps"],
                "dfsdt_verdict": dfsdt["verdict"],
                "dfsdt_rationale": dfsdt["rationale"],
            }
        )

    _RESULTS_DIR.mkdir(exist_ok=True)
    write_benchmark_csv(rows, _RESULTS_DIR / "benchmark_results.csv")
    write_comparison_table(rows, _RESULTS_DIR / "comparison_table.md")
    write_pass_rate_bar_chart(rows, _RESULTS_DIR / "pass_rate_comparison.png")

    print(f"\nWrote results to {_RESULTS_DIR}")


if __name__ == "__main__":
    main()
