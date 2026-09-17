from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str


class BaseLLM(ABC):
    """Pluggable interface for the model driving the reasoning loops.

    Any real model client can be wired in by implementing `generate`.
    """

    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError


class EchoLLM(BaseLLM):
    """Deterministic, scripted stand-in for a real language model.

    Used for local development and tests so the reasoning loops can be
    exercised without any network access or credentials.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        default_response: str = "Thought: no further guidance available.",
    ) -> None:
        self._responses = list(responses or [])
        self._default_response = default_response
        self._index = 0

    def generate(self, prompt: str) -> LLMResponse:
        if self._index < len(self._responses):
            text = self._responses[self._index]
            self._index += 1
        else:
            text = self._default_response
        return LLMResponse(text=text)
