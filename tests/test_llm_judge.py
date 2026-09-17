import csv

from agent.llm import EchoLLM
from eval.csv_export import write_judged_csv
from eval.llm_judge import (
    ComparisonVerdict,
    JudgedCase,
    JudgedComparison,
    LLMJudge,
    PassFailVerdict,
    judged_pass_rate,
    judged_win_rate,
    run_pass_rate_eval,
    run_win_rate_eval,
)


def test_judge_pass_parses_pass_verdict():
    llm = EchoLLM(responses=["Verdict: Pass\nRationale: The answer matches the expected result."])
    judge = LLMJudge(llm=llm)

    result = judge.judge_pass("What is 2 + 2?", "4")

    assert result.verdict is PassFailVerdict.PASS
    assert "matches" in result.rationale


def test_judge_pass_parses_fail_verdict():
    llm = EchoLLM(responses=["Verdict: Fail\nRationale: The answer is incorrect."])
    judge = LLMJudge(llm=llm)

    result = judge.judge_pass("What is 2 + 2?", "5")

    assert result.verdict is PassFailVerdict.FAIL


def test_judge_pass_falls_back_to_unsure_on_unparseable_response():
    llm = EchoLLM(responses=["I cannot decide."])
    judge = LLMJudge(llm=llm)

    result = judge.judge_pass("What is 2 + 2?", "4")

    assert result.verdict is PassFailVerdict.UNSURE


def test_compare_parses_winner_b():
    llm = EchoLLM(responses=["Verdict: B\nRationale: Solution B is more complete."])
    judge = LLMJudge(llm=llm)

    result = judge.compare("Summarize the article.", solution_a="short answer", solution_b="detailed answer")

    assert result.verdict is ComparisonVerdict.B


def test_compare_parses_tie():
    llm = EchoLLM(responses=["Verdict: Tie\nRationale: Both are equally good."])
    judge = LLMJudge(llm=llm)

    result = judge.compare("Summarize the article.", solution_a="answer one", solution_b="answer two")

    assert result.verdict is ComparisonVerdict.TIE


def test_judged_pass_rate_counts_pass_and_optionally_unsure():
    cases = [
        JudgedCase("a", PassFailVerdict.PASS, ""),
        JudgedCase("b", PassFailVerdict.FAIL, ""),
        JudgedCase("c", PassFailVerdict.UNSURE, ""),
    ]

    assert judged_pass_rate(cases) == 1 / 3
    assert judged_pass_rate(cases, count_unsure_as_pass=True) == 2 / 3


def test_judged_pass_rate_handles_empty_input():
    assert judged_pass_rate([]) == 0.0


def test_judged_win_rate_counts_a_and_ties():
    comparisons = [
        JudgedComparison("a", ComparisonVerdict.A, ""),
        JudgedComparison("b", ComparisonVerdict.TIE, ""),
        JudgedComparison("c", ComparisonVerdict.B, ""),
    ]

    assert judged_win_rate(comparisons) == 0.5


def test_write_judged_csv(tmp_path):
    cases = [JudgedCase("What is 2+2?", PassFailVerdict.PASS, "Correct.")]
    csv_path = tmp_path / "results.csv"

    write_judged_csv(cases, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["instruction", "verdict", "rationale"]
    assert rows[1] == ["What is 2+2?", "pass", "Correct."]


def test_run_pass_rate_eval_writes_csv(tmp_path):
    llm = EchoLLM(
        responses=[
            "Verdict: Pass\nRationale: Correct.",
            "Verdict: Fail\nRationale: Incorrect.",
        ]
    )
    judge = LLMJudge(llm=llm)
    csv_path = tmp_path / "pass_rate.csv"

    results = run_pass_rate_eval(
        judge,
        [("What is 2+2?", "4"), ("What is 2+2?", "5")],
        csv_path,
    )

    assert [r.verdict for r in results] == [PassFailVerdict.PASS, PassFailVerdict.FAIL]
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3


def test_run_win_rate_eval_writes_csv(tmp_path):
    llm = EchoLLM(responses=["Verdict: A\nRationale: A is better."])
    judge = LLMJudge(llm=llm)
    csv_path = tmp_path / "win_rate.csv"

    results = run_win_rate_eval(judge, [("Summarize.", "short", "long")], csv_path)

    assert results[0].verdict is ComparisonVerdict.A
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1] == ["Summarize.", "a", "A is better."]
