"""Runs one instruction through the ReAct agent and saves the full trace
(model text, tool calls, real tool observations and the answer) to
results/traces/, for the website's trace player.

Usage:
    python scripts/record_trace.py ["instruction"] [--name react_sample]

Requires an API key for the configured provider, like run_benchmark.py
(BENCHMARK_PROVIDER, BENCHMARK_MODEL), and network access for the tools.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv()

from agent.factory import build_llm, configured_model
from agent.react import ReActAgent
from apis.registry import keyless_registry
from retriever.retriever import APIRetriever

_TRACE_DIR = _ROOT / "results" / "traces"
_DEFAULT_INSTRUCTION = "How high above sea level is Lisbon, in feet?"


def _events(steps) -> list[dict]:
    """Splits each agent step into the events the trace player shows."""
    events = []
    for step in steps:
        lines = step.thought_or_action.splitlines()
        if step.tool_call is None:
            # Final step: "Finish[answer]", possibly after "No tool needed."
            for line in lines:
                if not line.startswith("Finish["):
                    events.append({"kind": "thought", "text": line})
            continue
        # A tool step: optional model text, then the requested call.
        for line in lines[:-1]:
            if line.strip():
                events.append({"kind": "thought", "text": line.strip()})
        events.append({"kind": "call", "text": lines[-1]})
        events.append({"kind": "observation", "text": step.observation or ""})
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instruction", nargs="?", default=_DEFAULT_INSTRUCTION)
    parser.add_argument("--name", default="react_sample", help="file name under results/traces/")
    parser.add_argument(
        "--top-k", type=int, default=0, help="candidate tools from the retriever (0: all tools, as in run_benchmark.py)"
    )
    args = parser.parse_args()

    registry = keyless_registry()
    candidates = registry.all()
    if args.top_k:
        candidates = [hit.api for hit in APIRetriever(candidates).retrieve(args.instruction, top_k=args.top_k)]
    llm, model = build_llm()
    result = ReActAgent(registry=registry, llm=llm).run(args.instruction, candidate_apis=candidates)

    events = _events(result.steps)
    if result.answer:
        events.append({"kind": "answer", "text": result.answer})
    trace = {
        "agent": "ReAct",
        "provider": configured_model()[0],
        "model": model,
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "instruction": args.instruction,
        "candidate_tools": [api.name for api in candidates],
        "stop_reason": result.stop_reason,
        "events": events,
    }
    _TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = _TRACE_DIR / f"{args.name}.json"
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for event in events:
        print(f"{event['kind']:>12}: {event['text']}")
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
