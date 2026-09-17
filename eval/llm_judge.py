from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from agent.anthropic_llm import AnthropicLLM
from agent.llm import BaseLLM

from .csv_export import write_judged_csv

_VERDICT_RE = re.compile(r"Verdict:\s*(\w+)", re.IGNORECASE)
_RATIONALE_RE = re.compile(r"Rationale:\s*(.+)", re.IGNORECASE | re.DOTALL)

_PASS_RATE_PROMPT = """You are grading whether an agent's final answer correctly and \
completely resolves the user's instruction. If you are not confident either way, say Unsure.

Instruction: {instruction}

Agent's final answer: {answer}

Respond in exactly this format:
Verdict: Pass|Fail|Unsure
Rationale: <one sentence>
"""

_WIN_RATE_PROMPT = """You are comparing two candidate solutions to the same instruction and \
deciding which one better resolves it. If they are equally good, say Tie. If you cannot tell,
say Unsure.

Instruction: {instruction}

Solution A:
{solution_a}

Solution B:
{solution_b}

Respond in exactly this format:
Verdict: A|B|Tie|Unsure
Rationale: <one sentence>
"""


class PassFailVerdict(Enum):
    PASS = "pass"
    FAIL = "fail"
    UNSURE = "unsure"


class ComparisonVerdict(Enum):
    A = "a"
    B = "b"
    TIE = "tie"
    UNSURE = "unsure"


@dataclass
class JudgedCase:
    instruction: str
    verdict: PassFailVerdict
    rationale: str = ""


@dataclass
class JudgedComparison:
    instruction: str
    verdict: ComparisonVerdict
    rationale: str = ""


def _parse_verdict(response: str, enum_cls):
    rationale_match = _RATIONALE_RE.search(response)
    rationale = rationale_match.group(1).strip() if rationale_match else ""

    verdict_match = _VERDICT_RE.search(response)
    if verdict_match:
        raw = verdict_match.group(1).strip().lower().strip(".:,;")
        for member in enum_cls:
            if member.value == raw:
                return member, rationale

    return enum_cls.UNSURE, rationale or "Could not parse a verdict from the model's response."


class LLMJudge:
    """Uses a language model to grade an agent's final answer as
    Pass/Fail/Unsure, or to pick the better of two candidate solutions to
    the same instruction. Defaults to `AnthropicLLM`; pass a different
    `BaseLLM` (e.g. `EchoLLM`) for offline testing.
    """

    def __init__(self, llm: BaseLLM | None = None) -> None:
        self._llm = llm if llm is not None else AnthropicLLM()

    def judge_pass(self, instruction: str, answer: str) -> JudgedCase:
        prompt = _PASS_RATE_PROMPT.format(instruction=instruction, answer=answer)
        response = self._llm.generate(prompt).text
        verdict, rationale = _parse_verdict(response, PassFailVerdict)
        return JudgedCase(instruction=instruction, verdict=verdict, rationale=rationale)

    def compare(self, instruction: str, solution_a: str, solution_b: str) -> JudgedComparison:
        prompt = _WIN_RATE_PROMPT.format(
            instruction=instruction, solution_a=solution_a, solution_b=solution_b
        )
        response = self._llm.generate(prompt).text
        verdict, rationale = _parse_verdict(response, ComparisonVerdict)
        return JudgedComparison(instruction=instruction, verdict=verdict, rationale=rationale)


def judged_pass_rate(cases: list[JudgedCase], count_unsure_as_pass: bool = False) -> float:
    if not cases:
        return 0.0
    passing = 0
    for case in cases:
        if case.verdict is PassFailVerdict.PASS:
            passing += 1
        elif case.verdict is PassFailVerdict.UNSURE and count_unsure_as_pass:
            passing += 1
    return passing / len(cases)


def judged_win_rate(comparisons: list[JudgedComparison], count_ties_as_half: bool = True) -> float:
    """Fraction of comparisons where solution A is judged the winner
    (ties counted as half by default)."""
    if not comparisons:
        return 0.0
    score = 0.0
    for comparison in comparisons:
        if comparison.verdict is ComparisonVerdict.A:
            score += 1.0
        elif comparison.verdict is ComparisonVerdict.TIE and count_ties_as_half:
            score += 0.5
    return score / len(comparisons)


def run_pass_rate_eval(
    judge: LLMJudge,
    cases: list[tuple[str, str]],
    output_csv: str | Path,
) -> list[JudgedCase]:
    """Judges each (instruction, answer) pair and writes the verdicts to
    `output_csv`."""
    results = [judge.judge_pass(instruction, answer) for instruction, answer in cases]
    write_judged_csv(results, output_csv)
    return results


def run_win_rate_eval(
    judge: LLMJudge,
    comparisons: list[tuple[str, str, str]],
    output_csv: str | Path,
) -> list[JudgedComparison]:
    """Judges each (instruction, solution_a, solution_b) triple and writes
    the verdicts to `output_csv`."""
    results = [judge.compare(instruction, solution_a, solution_b) for instruction, solution_a, solution_b in comparisons]
    write_judged_csv(results, output_csv)
    return results
