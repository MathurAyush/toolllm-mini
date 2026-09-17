from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    WIN = "win"
    LOSE = "lose"
    TIE = "tie"


@dataclass
class Comparison:
    instruction: str
    verdict: Verdict


def win_rate(comparisons: list[Comparison], count_ties_as_half: bool = True) -> float:
    if not comparisons:
        return 0.0
    score = 0.0
    for comparison in comparisons:
        if comparison.verdict is Verdict.WIN:
            score += 1.0
        elif comparison.verdict is Verdict.TIE and count_ties_as_half:
            score += 0.5
    return score / len(comparisons)
