from __future__ import annotations

from dataclasses import dataclass, field

from apis.registry import APIRegistry

from .anthropic_llm import AnthropicLLM
from .llm import BaseLLM, Message, ToolCall, ToolResultMessage, UserMessage
from .prompts import SYSTEM_PROMPT
from .tools import describe_turn, execute_tool_call, finish_text, function_declarations, tool_names


@dataclass
class Step:
    thought_or_action: str
    observation: str | None = None
    tool_call: ToolCall | None = None


@dataclass
class ReActResult:
    answer: str | None
    steps: list[Step] = field(default_factory=list)
    success: bool = False
    # Every tool call that was executed and returned a real result, in order.
    tool_calls: list[ToolCall] = field(default_factory=list)
    # "answered", "no_tool_needed" or "max_steps".
    stop_reason: str = "max_steps"


class ReActAgent:
    """Reason / act loop over a set of APIs using native function calling.

    Each step the model either requests tool calls, which the agent executes
    and returns as real function responses, or answers in plain text, which
    ends the run. An answer given without any tool call is reported with
    `stop_reason="no_tool_needed"`. The loop stops after `max_steps` model
    replies. Defaults to `AnthropicLLM`; pass a different `BaseLLM` (e.g.
    `GeminiLLM`, or `EchoLLM` offline and in tests).
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
        tools = function_declarations(candidate_apis)
        allowed = tool_names(candidate_apis)
        messages: list[Message] = [UserMessage(instruction)]
        steps: list[Step] = []
        executed: list[ToolCall] = []

        for _ in range(self._max_steps):
            turn = self._llm.chat(SYSTEM_PROMPT, messages, tools)

            if not turn.tool_calls:
                answer = turn.text.strip()
                if not answer:
                    continue  # empty reply: ask again, it still counts as a step
                used_tools = any(step.tool_call is not None for step in steps)
                steps.append(Step(thought_or_action=finish_text(answer, used_tools)))
                return ReActResult(
                    answer=answer,
                    steps=steps,
                    success=True,
                    tool_calls=executed,
                    stop_reason="answered" if used_tools else "no_tool_needed",
                )

            messages.append(turn)
            results = []
            for call in turn.tool_calls:
                result, observation = execute_tool_call(call, self._registry, allowed)
                results.append(result)
                if not result.is_error:
                    executed.append(call)
                steps.append(Step(describe_turn(turn, call), observation=observation, tool_call=call))
            messages.append(ToolResultMessage(results))

        return ReActResult(answer=None, steps=steps, success=False, tool_calls=executed, stop_reason="max_steps")
