from __future__ import annotations

import requests

from .base import APIResponse, BaseAPI


class QuoteAPI(BaseAPI):
    """Quotable - Random Quote

    Description:
        Returns a random inspirational quote and its author, optionally
        filtered by tag, from the public Quotable API. No authentication
        required.

    Required parameters:
        tags (str, optional): Comma-separated tag filter, e.g.
            "technology" or "wisdom,famous-quotes".

    Example response:
        {
            "content": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs"
        }
    """

    name = "random_quote"
    description = "Returns a random quote, optionally filtered by tag."
    parameters = {"tags": "Comma-separated tag filter, e.g. 'wisdom' (optional)."}

    _ENDPOINT = "https://api.quotable.io/random"

    def call(self, tags: str | None = None) -> APIResponse:
        params = {"tags": tags} if tags else {}
        try:
            response = requests.get(self._ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        data = {"content": payload.get("content"), "author": payload.get("author")}
        return APIResponse(success=True, data=data)
