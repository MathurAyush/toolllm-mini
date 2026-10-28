from __future__ import annotations

from dataclasses import dataclass, field

from apis.registry import APIRegistry

from .anthropic_llm import AnthropicLLM
from .events import EventHandler, emit
from .llm import BaseLLM, Message, ToolCall, ToolResultMessage, UserMessage
from .prompts import SYSTEM_PROMPT
from .react import Step
from .tools import describe_turn, execute_tool_call, finish_text, function_declarations, tool_names, turn_thought


@dataclass
class DFSDTResult:
    answer: str | None
    steps: list[Step] = field(default_factory=list)
    success: bool = False
    explored_paths: int = 0
    # Tool calls executed along the returned path, in order.
    tool_calls: list[ToolCall] = field(default_factory=list)
    # "answered", "no_tool_needed", "max_steps" or "exhausted".
    stop_reason: str = "exhausted"


@dataclass
class _Search:
    system: str
    tools: list[dict]
    allowed: set[str]
    explored: int = 0


class DFSDTAgent:
    """Depth-First Search-based Decision Tree reasoning loop using native
    function calling.

    At each node the agent samples up to `branching_factor` (breadth)
    candidate replies from the model. A plain-text reply is a final answer.
    A reply requesting tool calls is executed by the agent; if every call
    returns a real result the search goes one level deeper with those
    results, otherwise it backtracks and samples an alternative. Capped by
    default at depth 4 and breadth 3, and at `max_steps` model replies in
    total. Defaults to `AnthropicLLM`; pass a different `BaseLLM` (e.g.
    `GeminiLLM`, or `EchoLLM` offline and in tests). `on_event`, if given,
    is told about every sampled reply (a tree node, numbered from 1 in the
    order explored; 0 is the instruction), each tool call and each
    backtrack as they happen (see `agent.events`).
    """

    def __init__(
        self,
        registry: APIRegistry,
        llm: BaseLLM | None = None,
        max_depth: int = 4,
        branching_factor: int = 3,
        max_steps: int = 20,
        on_event: EventHandler | None = None,
    ) -> None:
        self._llm = llm if llm is not None else AnthropicLLM()
        self._registry = registry
        self._max_depth = max_depth
        self._branching_factor = branching_factor
        self._max_steps = max_steps
        self._on_event = on_event

    def run(self, instruction: str, candidate_apis: list) -> DFSDTResult:
        search = _Search(SYSTEM_PROMPT, function_declarations(candidate_apis), tool_names(candidate_apis))
        steps, answer = self._search(search, [UserMessage(instruction)], [], 0)

        used_tools = any(step.tool_call is not None for step in steps)
        if answer is not None:
            stop_reason = "answered" if used_tools else "no_tool_needed"
        elif search.explored >= self._max_steps:
            stop_reason = "max_steps"
        else:
            stop_reason = "exhausted"
        return DFSDTResult(
            answer=answer,
            steps=steps,
            success=answer is not None,
            explored_paths=search.explored,
            tool_calls=[step.tool_call for step in steps if step.tool_call is not None],
            stop_reason=stop_reason,
        )

    def _search(
        self,
        search: _Search,
        messages: list[Message],
        path: list[Step],
        depth: int,
        parent: int = 0,
    ) -> tuple[list[Step], str | None]:
        if depth >= self._max_depth:
            return path, None

        for _ in range(self._branching_factor):
            if search.explored >= self._max_steps:
                return path, None
            search.explored += 1
            node = search.explored
            turn = self._llm.chat(search.system, messages, search.tools)
            emit(
                self._on_event,
                "node",
                id=node,
                parent=parent,
                depth=depth + 1,
                tools=[call.name for call in turn.tool_calls],
            )

            if not turn.tool_calls:
                answer = turn.text.strip()
                if not answer:
                    emit(self._on_event, "backtrack", node=node, reason="empty_reply")
                    continue
                used_tools = any(step.tool_call is not None for step in path)
                emit(self._on_event, "answer", text=answer, node=node)
                return path + [Step(thought_or_action=finish_text(answer, used_tools))], answer

            results, new_steps = [], []
            for call in turn.tool_calls:
                result, observation = execute_tool_call(call, self._registry, search.allowed)
                emit(
                    self._on_event,
                    "step",
                    node=node,
                    thought=turn_thought(turn, call),
                    call=call,
                    result=result,
                    observation=observation,
                )
                if result.is_error:
                    emit(self._on_event, "backtrack", node=node, reason="tool_error")
                    break
                results.append(result)
                new_steps.append(Step(describe_turn(turn, call), observation=observation, tool_call=call))
            else:
                deeper_path, answer = self._search(
                    search,
                    messages + [turn, ToolResultMessage(results)],
                    path + new_steps,
                    depth + 1,
                    node,
                )
                if answer is not None:
                    return deeper_path, answer
                emit(self._on_event, "backtrack", node=node, reason="dead_end")

        return path, None
