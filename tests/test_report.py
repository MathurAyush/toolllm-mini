from eval.report import (
    build_comparison_table,
    pass_rate_by_complexity,
    write_benchmark_csv,
    write_comparison_table,
    write_pass_rate_bar_chart,
)

_ROWS = [
    {
        "id": "1",
        "instruction": "a",
        "complexity": "easy",
        "expected_apis": "calculator",
        "react_answer": "4",
        "react_steps": 2,
        "react_verdict": "pass",
        "react_rationale": "",
        "dfsdt_answer": "4",
        "dfsdt_steps": 3,
        "dfsdt_verdict": "pass",
        "dfsdt_rationale": "",
    },
    {
        "id": "2",
        "instruction": "b",
        "complexity": "easy",
        "expected_apis": "weather",
        "react_answer": "",
        "react_steps": 6,
        "react_verdict": "fail",
        "react_rationale": "",
        "dfsdt_answer": "sunny",
        "dfsdt_steps": 4,
        "dfsdt_verdict": "pass",
        "dfsdt_rationale": "",
    },
    {
        "id": "3",
        "instruction": "c",
        "complexity": "hard",
        "expected_apis": "search;country_info",
        "react_answer": "x",
        "react_steps": 5,
        "react_verdict": "unsure",
        "react_rationale": "",
        "dfsdt_answer": "y",
        "dfsdt_steps": 8,
        "dfsdt_verdict": "fail",
        "dfsdt_rationale": "",
    },
]


def test_pass_rate_by_complexity_overall_and_filtered():
    assert pass_rate_by_complexity(_ROWS, "react_verdict") == 1 / 3
    assert pass_rate_by_complexity(_ROWS, "dfsdt_verdict", "easy") == 1.0
    assert pass_rate_by_complexity(_ROWS, "dfsdt_verdict", "medium") == 0.0


def test_build_comparison_table_includes_all_tiers_and_overall():
    table = build_comparison_table(_ROWS)

    assert "easy" in table
    assert "hard" in table
    assert "overall" in table


def test_write_benchmark_csv(tmp_path):
    path = tmp_path / "results.csv"

    write_benchmark_csv(_ROWS, path)

    content = path.read_text(encoding="utf-8")
    assert "react_verdict" in content
    assert "sunny" in content


def test_write_comparison_table_to_file(tmp_path):
    path = tmp_path / "table.md"

    write_comparison_table(_ROWS, path)

    assert path.read_text(encoding="utf-8").startswith("| Complexity")


def test_write_pass_rate_bar_chart_creates_file(tmp_path):
    path = tmp_path / "chart.png"

    write_pass_rate_bar_chart(_ROWS, path)

    assert path.exists()
    assert path.stat().st_size > 0
