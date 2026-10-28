import csv
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "export_site_data.py"
_spec = importlib.util.spec_from_file_location("export_site_data", _SCRIPT)
export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export)


def test_wilson_interval_matches_known_values():
    low, high = export.wilson_interval(17, 19)
    assert low == pytest.approx(0.686, abs=1e-3)
    assert high == pytest.approx(0.971, abs=1e-3)
    assert export.wilson_interval(0, 0) is None


def test_wilson_interval_stays_within_bounds():
    for passed, n in [(0, 5), (5, 5), (1, 1)]:
        low, high = export.wilson_interval(passed, n)
        assert 0.0 <= low <= passed / n <= high <= 1.0


def test_ndcg_rewards_relevant_tools_ranked_first():
    assert export._ndcg(["a", "b", "c"], {"a"}, 5) == 1.0
    assert export._ndcg(["x", "a", "c"], {"a"}, 5) == pytest.approx(1 / 1.585, abs=1e-3)
    assert export._ndcg(["x", "y"], {"a"}, 5) == 0.0


def _write_csv(path, rows):
    fields = ["id", "complexity", "react_verdict", "react_steps", "dfsdt_verdict", "dfsdt_steps"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_pass_rates_groups_by_complexity(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "_ROOT", tmp_path)
    path = tmp_path / "results.csv"
    _write_csv(
        path,
        [
            {"id": "1", "complexity": "easy", "react_verdict": "pass", "react_steps": 1, "dfsdt_verdict": "fail", "dfsdt_steps": 2},
            {"id": "2", "complexity": "easy", "react_verdict": "unsure", "react_steps": 1, "dfsdt_verdict": "pass", "dfsdt_steps": 1},
            {"id": "3", "complexity": "hard", "react_verdict": "pass", "react_steps": 3, "dfsdt_verdict": "pass", "dfsdt_steps": 4},
        ],
    )
    out = export.pass_rates(path)
    easy = out["groups"][0]
    assert easy["complexity"] == "easy" and easy["n"] == 2
    assert easy["react"]["passed"] == 1 and easy["react"]["rate"] == 0.5
    assert out["groups"][1]["n"] == 0 and out["groups"][1]["react"]["rate"] is None
    assert out["overall"]["react"]["passed"] == 2 and out["overall"]["n"] == 3
    assert out["one_step_runs"] == {"count": 3, "of": 6}


def test_pass_rates_is_none_for_a_missing_file(tmp_path):
    assert export.pass_rates(tmp_path / "missing.csv") is None


def test_benchmark_summary_counts_tasks(tmp_path):
    tasks = [
        {"id": "gen-001", "instruction": "a", "difficulty": "easy", "expected_tools": ["x"], "expected_facts": ["1"], "split": "test"},
        {"id": "gen-002", "instruction": "b", "difficulty": "hard", "expected_tools": ["x", "y"], "split": "dev",
         "expected_value": {"check": "within 5% of the live tool result"}},
    ]
    path = tmp_path / "benchmark.jsonl"
    path.write_text("\n".join(json.dumps(t) for t in tasks) + "\n", encoding="utf-8")
    out = export.benchmark_summary(path)
    assert out["total"] == 2
    assert out["by_difficulty"] == {"easy": 1, "medium": 0, "hard": 1}
    assert out["by_split"] == {"dev": 1, "test": 1}
    assert (out["fact_tasks"], out["live_value_tasks"]) == (1, 1)
    assert [e["id"] for e in out["examples"]] == ["gen-001", "gen-002"]


def test_traces_drop_model_details(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "_ROOT", tmp_path)
    monkeypatch.setattr(export, "_RESULTS", tmp_path / "results")
    folder = tmp_path / "results" / "traces"
    folder.mkdir(parents=True)
    (folder / "t.json").write_text(
        json.dumps({"agent": "ReAct", "provider": "p", "model": "m", "candidate_tools": ["x"], "events": []}),
        encoding="utf-8",
    )
    [trace] = export.traces()
    assert trace == {"agent": "ReAct", "events": [], "source": "results/traces/t.json"}


def test_tool_pool_reports_registry_sizes():
    pool = export.tool_pool()
    assert pool["total"] == 49 and pool["keyless"] == 47
    assert pool["category_count"] == len(pool["categories"])
