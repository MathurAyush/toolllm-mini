from __future__ import annotations

import requests

from .base import APIResponse, BaseAPI


class JokeAPI(BaseAPI):
    """JokeAPI - Random Joke

    Description:
        Fetches a random joke, optionally restricted to a category, from
        the public JokeAPI service. No authentication required.

    Required parameters:
        category (str, optional): Joke category, one of "Any",
            "Programming", "Misc", "Dark", "Pun", "Spooky", "Christmas".
            Defaults to "Any".

    Example response:
        {
            "category": "Programming",
            "joke": "Why do programmers prefer dark mode? Because light attracts bugs."
        }
    """

    name = "joke"
    description = "Fetches a random joke, optionally filtered by category."
    parameters = {"category": "Joke category, e.g. 'Programming' (optional, defaults to 'Any')."}

    _ENDPOINT = "https://v2.jokeapi.dev/joke/{category}"

    def call(self, category: str = "Any") -> APIResponse:
        try:
            response = requests.get(
                self._ENDPOINT.format(category=category),
                params={"type": "single"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        if payload.get("error"):
            return APIResponse(success=False, error=payload.get("message", "JokeAPI returned an error."))

        joke_text = payload.get("joke") or f"{payload.get('setup')} ... {payload.get('delivery')}"
        data = {"category": payload.get("category", category), "joke": joke_text}
        return APIResponse(success=True, data=data)
