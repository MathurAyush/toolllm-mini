from __future__ import annotations

import os

from .llm import BaseLLM

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini": "gemini-3.5-flash-lite",
}


def configured_model() -> tuple[str, str]:
    """(provider, model) from BENCHMARK_PROVIDER and BENCHMARK_MODEL,
    defaulting to Gemini."""
    provider = os.environ.get("BENCHMARK_PROVIDER") or "gemini"
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unknown BENCHMARK_PROVIDER '{provider}' (expected 'anthropic' or 'gemini').")
    return provider, os.environ.get("BENCHMARK_MODEL") or DEFAULT_MODELS[provider]


def build_llm(max_retries: int | None = None) -> tuple[BaseLLM, str]:
    """The configured LLM backend and its model id. `max_retries` caps the
    Gemini backend's retries on rate-limit and server errors."""
    provider, model = configured_model()
    if provider == "anthropic":
        from .anthropic_llm import AnthropicLLM

        return AnthropicLLM(model=model), model
    from .gemini_llm import GeminiLLM

    if max_retries is None:
        return GeminiLLM(model=model), model
    return GeminiLLM(model=model, max_retries=max_retries), model
