from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class LLMResponse:
    text: str


@dataclass
class ToolCall:
    """A tool call requested by the model. Only a request: the agent decides
    whether to run it and produces the result itself."""

    name: str
    args: dict = field(default_factory=dict)
    id: str | None = None


@dataclass
class ModelTurn:
    """One model reply: optional text and zero or more tool call requests.

    `raw` holds the provider's own message object so it can be replayed
    verbatim in later requests (Gemini needs this for thought signatures).
    """

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


@dataclass
class UserMessage:
    text: str


@dataclass
class ToolResult:
    """The real result of executing a `ToolCall`, sent back to the model as
    a function response."""

    call: ToolCall
    response: dict
    is_error: bool = False


@dataclass
class ToolResultMessage:
    results: list[ToolResult]


Message = Union[UserMessage, ModelTurn, ToolResultMessage]


class BaseLLM(ABC):
    """Pluggable interface for the model driving the reasoning loops.

    `generate` is plain text in, text out (used by the LLM judge).
    `chat` is native function calling: the model sees the tool declarations
    and either answers in text or requests tool calls, which the agent runs.
    """

    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> ModelTurn:
        raise NotImplementedError(f"{type(self).__name__} does not support tool calling.")


ScriptedTurn = Union[str, ToolCall, list, ModelTurn]


class EchoLLM(BaseLLM):
    """Deterministic, scripted stand-in for a real language model.

    Used for local development and tests so the reasoning loops can be
    exercised without any network access or credentials. For `chat`, each
    scripted response is a final text answer (str), a tool call request
    (`ToolCall`, or a list of them), or a full `ModelTurn`. Every request
    is recorded in `requests` so tests can check what the model was sent.
    """

    def __init__(
        self,
        responses: list[ScriptedTurn] | None = None,
        default_response: ScriptedTurn = "Thought: no further guidance available.",
    ) -> None:
        self._responses = list(responses or [])
        self._default_response = default_response
        self._index = 0
        self.requests: list[dict] = []

    def _next(self) -> ScriptedTurn:
        if self._index < len(self._responses):
            item = self._responses[self._index]
            self._index += 1
            return item
        return self._default_response

    def generate(self, prompt: str) -> LLMResponse:
        item = self._next()
        return LLMResponse(text=item if isinstance(item, str) else str(item))

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> ModelTurn:
        self.requests.append({"system": system, "messages": list(messages), "tools": tools})
        item = self._next()
        if isinstance(item, ModelTurn):
            return item
        if isinstance(item, ToolCall):
            return ModelTurn(tool_calls=[item])
        if isinstance(item, list):
            return ModelTurn(tool_calls=list(item))
        return ModelTurn(text=item)
