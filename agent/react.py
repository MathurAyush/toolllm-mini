from __future__ import annotations

from dataclasses import dataclass, field

from apis.registry import APIRegistry

from .anthropic_llm import AnthropicLLM
from .llm import BaseLLM
from .parsing import parse_action, parse_args, parse_finish
from .prompts import build_prompt


@dataclass
class Step:
    thought_or_action: str
    observation: str | None = None


@dataclass
class ReActResult:
    answer: str | None
    steps: list[Step] = field(default_factory=list)
    success: bool = False


class ReActAgent:
    """Thought / Action / Observation reasoning loop over a set of APIs.

    Repeats Thought -> Action (API call) -> Observation until the model
    emits Finish[...] or `max_steps` is exhausted. Defaults to
    `AnthropicLLM` for the reasoning calls; pass a different `BaseLLM`
    (e.g. `EchoLLM`) to run offline or in tests.
    """

    def __init__(
        self,
        registry: APIRegistry,
        llm: BaseLLM | None = None,
        max_steps: int = 6,
    ) -> None:
        self._llm = llm if llm is not None else AnthropicLLM()
        self._registry = registry
        self._max_steps = max_steps

    def run(self, instruction: str, candidate_apis: list) -> ReActResult:
        api_descriptions = "\n".join(f"- {api.name}: {api.description}" for api in candidate_apis)
        history = ""
        steps: list[Step] = []

        for _ in range(self._max_steps):
            prompt = build_prompt(instruction, api_descriptions, history)
            response = self._llm.generate(prompt).text
            history += response + "\n"

            finish_match = parse_finish(response)
            if finish_match:
                steps.append(Step(thought_or_action=response))
                return ReActResult(answer=finish_match.group(1).strip(), steps=steps, success=True)

            action_match = parse_action(response)
            if action_match:
                api_name, raw_args = action_match.groups()
                api = self._registry.get(api_name)
                if api is None:
                    observation = f"Error: unknown API '{api_name}'."
                else:
                    kwargs = parse_args(raw_args, api)
                    result = api.call(**kwargs)
                    observation = str(result.data) if result.success else f"Error: {result.error}"
                history += f"Observation: {observation}\n"
                steps.append(Step(thought_or_action=response, observation=observation))
            else:
                steps.append(Step(thought_or_action=response))

        return ReActResult(answer=None, steps=steps, success=False)
