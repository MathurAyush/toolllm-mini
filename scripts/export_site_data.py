"""Exports the numbers the website shows to site/data/results.json (and
the same data as site/data/results.js, so the pages also work when opened
straight from disk, where browsers block fetch()).

Usage:
    python scripts/export_site_data.py [--no-semantic]

Reads:
  - results/benchmark_results.csv: the Phase 1 ReAct vs DFSDT run, with
    Wilson 95% confidence intervals. Marked provisional: it predates the
    fix for made-up tool results.
  - results/verified_results.csv, if present: the same columns from a run
    after the fixes. Missing values are exported as null and the site
    shows them as TBD.
  - results/traces/*.json: recorded agent traces for the trace player.
  - data/benchmark.jsonl: the generated benchmark.
  - the tool registry, for the tool pool size and categories.
  - site/assets/video/demo.mp4, if present, for the demo video.
It also scores the retrievers on the benchmark's expected tools (no model
calls; MiniLM runs locally unless --no-semantic).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from apis.registry import full_registry, keyless_registry

_RESULTS = _ROOT / "results"
_DATA = _ROOT / "data"
_SITE_DATA = _ROOT / "site" / "data"
_DIFFICULTIES = ("easy", "medium", "hard")
# The Phase 1 pool: the 9 keyless tools the first benchmark ran with.
_PHASE1_TOOL_COUNT = 9


def wilson_interval(passed: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval for a pass rate; None when there are no runs."""
    if n == 0:
        return None
    p = passed / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _rate(passed: int, n: int) -> dict:
    interval = wilson_interval(passed, n)
    return {
        "passed": passed,
        "n": n,
        "rate": passed / n if n else None,
        "ci_low": interval[0] if interval else None,
        "ci_high": interval[1] if interval else None,
    }


def pass_rates(path: Path) -> dict | None:
    """Pass rate per complexity and overall for each agent in a benchmark
    CSV (only a "pass" verdict counts)."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups = [(d, [r for r in rows if r["complexity"] == d]) for d in _DIFFICULTIES] + [("overall", rows)]
    out = {"source": path.relative_to(_ROOT).as_posix(), "groups": []}
    for name, group in groups:
        entry = {"complexity": name, "n": len(group)}
        for agent in ("react", "dfsdt"):
            entry[agent] = _rate(sum(r[f"{agent}_verdict"] == "pass" for r in group), len(group))
        out["groups"].append(entry)
    out["overall"] = out["groups"][-1]
    one_step = sum(int(r[f"{agent}_steps"]) == 1 for r in rows for agent in ("react", "dfsdt"))
    out["one_step_runs"] = {"count": one_step, "of": 2 * len(rows)}
    return out


def benchmark_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_difficulty = Counter(t["difficulty"] for t in tasks)
    by_split = Counter(t.get("split", "") for t in tasks)
    return {
        "total": len(tasks),
        "by_difficulty": {d: by_difficulty[d] for d in _DIFFICULTIES},
        "by_split": {s: by_split[s] for s in ("dev", "test")},
        "live_value_tasks": sum("expected_value" in t for t in tasks),
        "fact_tasks": sum("expected_facts" in t for t in tasks),
        "examples": [_example(t) for t in _spread(tasks)],
    }


def _spread(tasks: list[dict]) -> list[dict]:
    """One task of each difficulty, plus one live-data task."""
    picks = [next((t for t in tasks if t["difficulty"] == d), None) for d in _DIFFICULTIES]
    picks.append(next((t for t in tasks if "expected_value" in t), None))
    seen, out = set(), []
    for task in picks:
        if task and task["id"] not in seen:
            seen.add(task["id"])
            out.append(task)
    return out


def _example(task: dict) -> dict:
    check = task["expected_value"]["check"] if "expected_value" in task else ", ".join(task["expected_facts"])
    return {
        "id": task["id"],
        "instruction": task["instruction"],
        "difficulty": task["difficulty"],
        "tools": task["expected_tools"],
        "check": check,
    }


def _ndcg(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, name in enumerate(ranked[:k]) if name in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def retriever_scores(tasks: list[tuple[str, list[str]]], semantic: bool) -> dict:
    """Top-1 accuracy, recall@3 and NDCG@5 of each retriever over
    (instruction, expected tools) pairs, ranking the keyless pool."""
    from retriever import APIRetriever, KeywordMatchRetriever

    apis = keyless_registry().all()
    retrievers = [("Keyword overlap", KeywordMatchRetriever(apis)), ("TF-IDF (stemmed)", APIRetriever(apis))]
    if semantic:
        try:
            from retriever import SentenceTransformerEmbedder

            retrievers.append(("MiniLM embeddings", APIRetriever(apis, embedder=SentenceTransformerEmbedder())))
        except Exception as exc:  # model or library unavailable: leave it out
            print(f"Skipping the MiniLM retriever: {exc!r}")

    out = []
    for name, retriever in retrievers:
        top1 = recall3 = ndcg5 = 0.0
        for instruction, expected in tasks:
            ranked = [hit.api.name for hit in retriever.retrieve(instruction, top_k=5)]
            relevant = set(expected)
            top1 += ranked[0] in relevant
            recall3 += len(relevant & set(ranked[:3])) / len(relevant)
            ndcg5 += _ndcg(ranked, relevant, 5)
        n = len(tasks)
        out.append({"name": name, "top1": top1 / n, "recall_at_3": recall3 / n, "ndcg_at_5": ndcg5 / n})
    # Planned, not built yet: shown as TBD on the site.
    out += [{"name": label, "top1": None, "recall_at_3": None, "ndcg_at_5": None} for label in ("BM25", "Hybrid")]
    return {"n_tasks": len(tasks), "pool_size": len(apis), "retrievers": out}


def _retriever_tasks() -> tuple[list[tuple[str, list[str]]], str]:
    generated = _DATA / "benchmark.jsonl"
    if generated.exists():
        lines = generated.read_text(encoding="utf-8").splitlines()
        tasks = [json.loads(line) for line in lines if line.strip()]
        return [(t["instruction"], t["expected_tools"]) for t in tasks], "data/benchmark.jsonl"
    items = json.loads((_DATA / "benchmark_instructions.json").read_text(encoding="utf-8"))
    return [(t["instruction"], t["expected_apis"]) for t in items], "data/benchmark_instructions.json"


def tool_pool() -> dict:
    full, keyless = full_registry(), keyless_registry()
    categories = Counter(api.category for api in full.all())
    return {
        "phase1": _PHASE1_TOOL_COUNT,
        "total": len(full.all()),
        "keyless": len(keyless.all()),
        "category_count": len(categories),
        "categories": dict(categories.most_common()),
        "tools": [{"name": api.name, "category": api.category} for api in full.all()],
    }


def traces() -> list[dict]:
    folder = _RESULTS / "traces"
    if not folder.exists():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        # The site shows what the agent did, not which hosted model ran it.
        for key in ("candidate_tools", "provider", "model"):
            trace.pop(key, None)
        trace["source"] = path.relative_to(_ROOT).as_posix()
        out.append(trace)
    return out


def media() -> dict:
    """Optional media files the site shows when present. Recording whether
    they exist lets the page skip a request that would only 404."""
    video = _ROOT / "site" / "assets" / "video" / "demo.mp4"
    return {"demo_video": "assets/video/demo.mp4" if video.exists() else None}


def build(semantic: bool = True) -> dict:
    retriever_tasks, retriever_source = _retriever_tasks()
    retriever = retriever_scores(retriever_tasks, semantic)
    retriever["source"] = retriever_source
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "tools": tool_pool(),
        "baseline": pass_rates(_RESULTS / "benchmark_results.csv"),
        "verified": pass_rates(_RESULTS / "verified_results.csv"),
        "benchmark": benchmark_summary(_DATA / "benchmark.jsonl"),
        "retriever": retriever,
        "traces": traces(),
        "media": media(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-semantic", action="store_true", help="skip the MiniLM retriever")
    args = parser.parse_args()

    data = build(semantic=not args.no_semantic)
    _SITE_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=1, ensure_ascii=False)
    (_SITE_DATA / "results.json").write_text(text + "\n", encoding="utf-8")
    (_SITE_DATA / "results.js").write_text(
        "// Generated by scripts/export_site_data.py; do not edit.\nwindow.SITE_RESULTS = " + text + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {_SITE_DATA / 'results.json'} and results.js")


if __name__ == "__main__":
    main()
