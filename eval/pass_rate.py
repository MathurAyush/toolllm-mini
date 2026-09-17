from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalCase:
    instruction: str
    success: bool


def pass_rate(cases: list[EvalCase]) -> float:
    if not cases:
        return 0.0
    return sum(1 for c in cases if c.success) / len(cases)
