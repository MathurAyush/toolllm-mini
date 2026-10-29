"""Records real runs of the demo's example questions (data/demo_questions.json)
with both agents, exactly as the live demo server returns them, to
results/demo_runs/. scripts/export_site_data.py copies them to the site,
where the demo page replays them, labelled as recorded, when no server is
reachable (for example on GitHub Pages).

Usage:
    python scripts/record_demo_runs.py [--only N] [--top-k 5]

Requires the model key in .env and network access for the tools.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

from agent.factory import build_llm
from apis.registry import keyless_registry
from retriever.retriever import APIRetriever
from server.runner import STRATEGIES, Limits, friendly_error, run_question, validate

_QUESTIONS = _ROOT / "data" / "demo_questions.json"
_OUT = _ROOT / "results" / "demo_runs"


def slug(question: str) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", question.lower())[:6])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", type=int, help="record only question N (1-based)")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    questions = json.loads(_QUESTIONS.read_text(encoding="utf-8"))
    if args.only:
        questions = [questions[args.only - 1]]
    registry = keyless_registry()
    retriever = APIRetriever(registry.all())
    limits = Limits()
    _OUT.mkdir(parents=True, exist_ok=True)

    for question in questions:
        for strategy in STRATEGIES:
            params = validate(question, strategy, args.top_k, limits)
            llm, model = build_llm()
            try:
                run = run_question(params, registry=registry, retriever=retriever, llm=llm, model=model, limits=limits)
            except Exception as exc:  # noqa: BLE001 - report and keep going
                print(f"FAILED {strategy}: {question} ({friendly_error(exc).message})")
                continue
            run["recorded_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            path = _OUT / f"{slug(question)}_{strategy}.json"
            path.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"{strategy:>6} {run['num_tool_calls']} calls, {run['latency_ms']} ms: {question}")
            print(f"       -> {run['final_answer']}")


if __name__ == "__main__":
    main()
