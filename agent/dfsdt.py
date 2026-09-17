from __future__ import annotations

from dataclasses import dataclass, field

from apis.registry import APIRegistry

from .anthropic_llm import AnthropicLLM
from .llm import BaseLLM
from .parsing import parse_action, parse_args, parse_finish
from .prompts import build_prompt
from .react import Step


@dataclass
class DFSDTResult:
    answer: str | None
    steps: list[Step] = field(default_factory=list)
    success: bool = False
    explored_paths: int = 0


class DFSDTAgent:
    """Depth-First Search-based Decision Tree reasoning loop.

    At each node the agent samples up to `branching_factor` (breadth)
    candidate next steps from the underlying model, follows the first
    branch whose action succeeds, and backtracks to try an alternate
    action whenever a branch fails, looks unproductive (no parseable
    action), or the depth budget is exhausted before reaching Finish.
    Capped by default at depth 4 and breadth 3. Defaults to
    `AnthropicLLM` for the reasoning calls; pass a different `BaseLLM`
    (e.g. `EchoLLM`) to run offline or in tests.
    """

    def __init__(
        self,
        registry: APIRegistry,
        llm: BaseLLM | None = None,
        max_depth: int = 4,
        branching_factor: int = 3,
    ) -> None:
        self._llm = llm if llm is not None else AnthropicLLM()
        self._registry = registry
        self._max_depth = max_depth
        self._branching_factor = branching_factor

    def run(self, instruction: str, candidate_apis: list) -> DFSDTResult:
        api_descriptions = "\n".join(f"- {api.name}: {api.description}" for api in candidate_apis)
        explored = {"count": 0}
        steps, answer = self._search(instruction, api_descriptions, "", [], 0, explored)
        return DFSDTResult(
            answer=answer,
            steps=steps,
            success=answer is not None,
            explored_paths=explored["count"],
        )

    def _search(
        self,
        instruction: str,
        api_descriptions: str,
        history: str,
        path: list[Step],
        depth: int,
        explored: dict,
    ) -> tuple[list[Step], str | None]:
        if depth >= self._max_depth:
            return path, None

        for _ in range(self._branching_factor):
            explored["count"] += 1
            prompt = build_prompt(instruction, api_descriptions, history)
            response = self._llm.generate(prompt).text

            finish_match = parse_finish(response)
            if finish_match:
                return path + [Step(thought_or_action=response)], finish_match.group(1).strip()

            action_match = parse_action(response)
            if not action_match:
                continue

            api_name, raw_args = action_match.groups()
            api = self._registry.get(api_name)
            if api is None:
                continue

            kwargs = parse_args(raw_args, api)
            try:
                result = api.call(**kwargs)
            except Exception:
                continue
            if not result.success:
                continue

            observation = str(result.data)
            new_history = history + response + f"\nObservation: {observation}\n"
            new_path = path + [Step(thought_or_action=response, observation=observation)]
            deeper_path, answer = self._search(
                instruction, api_descriptions, new_history, new_path, depth + 1, explored
            )
            if answer is not None:
                return deeper_path, answer

        return path, None
