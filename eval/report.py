from __future__ import annotations

import csv
from pathlib import Path

BENCHMARK_FIELDNAMES = [
    "id",
    "instruction",
    "complexity",
    "expected_apis",
    "react_answer",
    "react_steps",
    "react_verdict",
    "react_rationale",
    "dfsdt_answer",
    "dfsdt_steps",
    "dfsdt_verdict",
    "dfsdt_rationale",
]

COMPLEXITY_TIERS = ["easy", "medium", "hard"]


def pass_rate_by_complexity(rows: list[dict], verdict_key: str, complexity: str | None = None) -> float:
    subset = [row for row in rows if complexity is None or row["complexity"] == complexity]
    if not subset:
        return 0.0
    passing = sum(1 for row in subset if row[verdict_key] == "pass")
    return passing / len(subset)


def write_benchmark_csv(rows: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BENCHMARK_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_comparison_table(rows: list[dict]) -> str:
    lines = ["| Complexity | ReAct pass rate | DFSDT pass rate | N |", "| --- | --- | --- | --- |"]
    for tier in COMPLEXITY_TIERS:
        n = sum(1 for row in rows if row["complexity"] == tier)
        lines.append(
            f"| {tier} | {pass_rate_by_complexity(rows, 'react_verdict', tier):.0%} "
            f"| {pass_rate_by_complexity(rows, 'dfsdt_verdict', tier):.0%} | {n} |"
        )
    lines.append(
        f"| **overall** | **{pass_rate_by_complexity(rows, 'react_verdict'):.0%}** "
        f"| **{pass_rate_by_complexity(rows, 'dfsdt_verdict'):.0%}** | {len(rows)} |"
    )
    return "\n".join(lines) + "\n"


def write_comparison_table(rows: list[dict], path: str | Path) -> None:
    Path(path).write_text(build_comparison_table(rows), encoding="utf-8")


def write_pass_rate_bar_chart(rows: list[dict], path: str | Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tiers = COMPLEXITY_TIERS + ["overall"]
    react_rates = [pass_rate_by_complexity(rows, "react_verdict", t if t != "overall" else None) for t in tiers]
    dfsdt_rates = [pass_rate_by_complexity(rows, "dfsdt_verdict", t if t != "overall" else None) for t in tiers]

    positions = range(len(tiers))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([p - width / 2 for p in positions], react_rates, width, label="ReAct", color="#4C72B0")
    ax.bar([p + width / 2 for p in positions], dfsdt_rates, width, label="DFSDT", color="#DD8452")
    ax.set_xticks(list(positions))
    ax.set_xticklabels([t.capitalize() for t in tiers])
    ax.set_ylabel("Pass rate")
    ax.set_ylim(0, 1)
    ax.set_title("ReAct vs DFSDT pass rate by instruction complexity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
