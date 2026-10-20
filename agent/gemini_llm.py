from __future__ import annotations

import os
import time

from .llm import BaseLLM, LLMResponse, Message, ModelTurn, ToolCall, ToolResultMessage, UserMessage

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiLLM(BaseLLM):
    """Google Gemini API - reasoning backend

    Description:
        Drives the ReAct/DFSDT loops with a real language model via the
        Google Gen AI SDK (`google-genai`), using native function calling:
        each candidate API is declared as a function, the model can only
        request calls, and the agent sends back the real results as
        function responses. Automatic function calling is disabled so the
        SDK never runs anything itself. Retries with exponential backoff on
        transient rate-limit/server errors (HTTP 429/500/502/503/504).

    Required parameters:
        model (str, optional): Model id to call. Defaults to
            "gemini-3.5-flash-lite".
        api_key (str, optional): API key. Falls back to the
            GEMINI_API_KEY environment variable if omitted.
    """

    def __init__(
        self,
        model: str = "gemini-3.5-flash-lite",
        api_key: str | None = None,
        max_retries: int = 5,
    ) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing Gemini API key (set GEMINI_API_KEY).")

        from google.genai import errors, types

        self._api_error = errors.APIError
        self._types = types
        self._client = self._make_client(key)
        self._model = model
        self._max_retries = max_retries

    @staticmethod
    def _make_client(key: str):
        from google import genai

        return genai.Client(api_key=key)

    def _with_retries(self, **kwargs):
        delay = 2.0
        for attempt in range(self._max_retries + 1):
            try:
                return self._client.models.generate_content(model=self._model, **kwargs)
            except self._api_error as exc:
                is_retryable = getattr(exc, "code", None) in _RETRYABLE_STATUS_CODES
                if not is_retryable or attempt == self._max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")

    def generate(self, prompt: str) -> LLMResponse:
        response = self._with_retries(contents=prompt)
        return LLMResponse(text=response.text)

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> ModelTurn:
        types = self._types
        config = types.GenerateContentConfig(
            system_instruction=system,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if tools:
            config.tools = [types.Tool(function_declarations=[self._declaration(t) for t in tools])]
            config.tool_config = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode=types.FunctionCallingConfigMode.AUTO)
            )
        response = self._with_retries(contents=[self._content(m) for m in messages], config=config)
        return self._to_turn(response)

    def _declaration(self, tool: dict):
        return self._types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters_json_schema=tool["parameters"],
        )

    def _content(self, message: Message):
        types = self._types
        if isinstance(message, UserMessage):
            return types.Content(role="user", parts=[types.Part(text=message.text)])
        if isinstance(message, ModelTurn):
            if message.raw is not None:
                # Replayed as returned, so thought signatures stay intact.
                return message.raw
            parts = [types.Part(text=message.text)] if message.text else []
            parts += [
                types.Part(function_call=types.FunctionCall(id=c.id, name=c.name, args=c.args))
                for c in message.tool_calls
            ]
            return types.Content(role="model", parts=parts)
        if isinstance(message, ToolResultMessage):
            return types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=r.call.id, name=r.call.name, response=r.response
                        )
                    )
                    for r in message.results
                ],
            )
        raise TypeError(f"Unsupported message type: {type(message).__name__}")

    @staticmethod
    def _to_turn(response) -> ModelTurn:
        candidates = response.candidates or []
        content = candidates[0].content if candidates else None
        parts = (content.parts if content else None) or []
        text = "".join(p.text for p in parts if p.text and not p.thought)
        calls = [
            ToolCall(name=p.function_call.name, args=dict(p.function_call.args or {}), id=p.function_call.id)
            for p in parts
            if p.function_call is not None
        ]
        return ModelTurn(text=text, tool_calls=calls, raw=content)
