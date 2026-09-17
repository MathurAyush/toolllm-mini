from eval.metrics import judge_pass
from eval.pass_rate import EvalCase, pass_rate
from eval.win_rate import Comparison, Verdict, win_rate


def test_pass_rate_computes_fraction_of_successes():
    cases = [EvalCase("a", True), EvalCase("b", False), EvalCase("c", True), EvalCase("d", True)]
    assert pass_rate(cases) == 0.75


def test_pass_rate_handles_empty_input():
    assert pass_rate([]) == 0.0


def test_win_rate_counts_ties_as_half_by_default():
    comparisons = [
        Comparison("a", Verdict.WIN),
        Comparison("b", Verdict.TIE),
        Comparison("c", Verdict.LOSE),
        Comparison("d", Verdict.WIN),
    ]
    assert win_rate(comparisons) == 0.625


def test_win_rate_can_ignore_ties():
    comparisons = [Comparison("a", Verdict.WIN), Comparison("b", Verdict.TIE)]
    assert win_rate(comparisons, count_ties_as_half=False) == 0.5


def test_judge_pass_matches_expected_keywords():
    case = judge_pass("Where is the Eiffel Tower?", "It is located in Paris, France.", ["paris"])
    assert case.success


def test_judge_pass_fails_on_missing_keyword():
    case = judge_pass("Where is the Eiffel Tower?", "It is a large iron structure.", ["paris"])
    assert not case.success


def test_judge_pass_fails_when_answer_missing():
    case = judge_pass("Unanswerable", None, ["anything"])
    assert not case.success
