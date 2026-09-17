from __future__ import annotations

from .pass_rate import EvalCase


def judge_pass(instruction: str, answer: str | None, expected_keywords: list[str]) -> EvalCase:
    """Scores an agent's final answer by checking that every expected
    keyword appears in it, case-insensitively."""
    if answer is None:
        return EvalCase(instruction=instruction, success=False)
    normalized = answer.lower()
    success = all(keyword.lower() in normalized for keyword in expected_keywords)
    return EvalCase(instruction=instruction, success=success)
