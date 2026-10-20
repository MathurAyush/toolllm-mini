from __future__ import annotations

import json
import os

from .llm import BaseLLM, LLMResponse, Message, ModelTurn, ToolCall, ToolResultMessage, UserMessage


class AnthropicLLM(BaseLLM):
    """Anthropic Messages API - reasoning backend

    Description:
        Drives the ReAct/DFSDT loops with a real language model via the
        Anthropic Messages API, using native tool use: the model can only
        request tool calls, and the agent sends back the real results as
        tool_result blocks.

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

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> ModelTurn:
        kwargs = {}
        if tools:
            kwargs["tools"] = [
                {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                for t in tools
            ]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[self._message(m) for m in messages],
            **kwargs,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        calls = [
            ToolCall(name=block.name, args=dict(block.input or {}), id=block.id)
            for block in response.content
            if block.type == "tool_use"
        ]
        return ModelTurn(text=text, tool_calls=calls, raw=response.content)

    @staticmethod
    def _message(message: Message) -> dict:
        if isinstance(message, UserMessage):
            return {"role": "user", "content": message.text}
        if isinstance(message, ModelTurn):
            if message.raw is not None:
                return {"role": "assistant", "content": message.raw}
            content = [{"type": "text", "text": message.text}] if message.text else []
            content += [
                {"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in message.tool_calls
            ]
            return {"role": "assistant", "content": content}
        if isinstance(message, ToolResultMessage):
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": r.call.id,
                        "content": json.dumps(r.response),
                        "is_error": r.is_error,
                    }
                    for r in message.results
                ],
            }
        raise TypeError(f"Unsupported message type: {type(message).__name__}")
