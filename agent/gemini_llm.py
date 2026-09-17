from __future__ import annotations

import os
import time

from .llm import BaseLLM, LLMResponse

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiLLM(BaseLLM):
    """Google Gemini API - reasoning backend

    Description:
        Drives the ReAct/DFSDT Thought/Action/Observation loop with a
        real language model, via the Google Gemini API. Alternative
        backend to `AnthropicLLM` for accounts using a Gemini API key.
        Retries with exponential backoff on transient rate-limit/server
        errors (HTTP 429/500/502/503/504).

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

        from google.genai import errors

        self._api_error = errors.APIError
        self._client = self._make_client(key)
        self._model = model
        self._max_retries = max_retries

    @staticmethod
    def _make_client(key: str):
        from google import genai

        return genai.Client(api_key=key)

    def generate(self, prompt: str) -> LLMResponse:
        delay = 2.0
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.models.generate_content(model=self._model, contents=prompt)
                return LLMResponse(text=response.text)
            except self._api_error as exc:
                is_retryable = getattr(exc, "code", None) in _RETRYABLE_STATUS_CODES
                if not is_retryable or attempt == self._max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")
