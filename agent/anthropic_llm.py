from __future__ import annotations

import os

from .llm import BaseLLM, LLMResponse


class AnthropicLLM(BaseLLM):
    """Anthropic Messages API - reasoning backend

    Description:
        Drives the ReAct/DFSDT Thought/Action/Observation loop with a
        real language model, via the Anthropic Messages API.

    Required parameters:
        model (str, optional): Model id to call. Defaults to
            "claude-sonnet-5".
        api_key (str, optional): API key. Falls back to the
            ANTHROPIC_API_KEY environment variable if omitted.
        max_tokens (int, optional): Maximum tokens to generate per call.
            Defaults to 512.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        api_key: str | None = None,
        max_tokens: int = 512,
    ) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Missing Anthropic API key (set ANTHROPIC_API_KEY).")

        import anthropic

        self._client = anthropic.Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, prompt: str) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(text=text)
