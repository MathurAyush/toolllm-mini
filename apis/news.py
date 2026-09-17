from __future__ import annotations

import os

import requests

from .base import APIResponse, BaseAPI


class NewsAPI(BaseAPI):
    """NewsAPI - Top Headlines

    Description:
        Returns the latest top headlines for a given country and/or
        search query, via NewsAPI.org. Requires a free API key.

    Required parameters:
        query (str, optional): Keyword(s) to search for within headlines.
        country (str, optional): Two-letter country code, e.g. "us".
            Defaults to "us" when neither query nor country is given.
        api_key (str, optional): NewsAPI key from https://newsapi.org.
            Falls back to the NEWSAPI_KEY environment variable if omitted.

    Example response:
        {
            "total_results": 34,
            "articles": [
                {
                    "title": "Example Headline",
                    "source": "Example News",
                    "url": "https://example.com/article"
                }
            ]
        }
    """

    name = "news_headlines"
    description = "Returns top news headlines, optionally filtered by keyword or country."
    parameters = {
        "query": "Keyword(s) to search for within headlines (optional).",
        "country": "Two-letter country code, e.g. 'us' (optional, defaults to 'us').",
        "api_key": "NewsAPI key (optional if NEWSAPI_KEY is set).",
    }

    _ENDPOINT = "https://newsapi.org/v2/top-headlines"

    def call(
        self,
        query: str | None = None,
        country: str | None = None,
        api_key: str | None = None,
    ) -> APIResponse:
        key = api_key or os.environ.get("NEWSAPI_KEY")
        if not key:
            return APIResponse(success=False, error="Missing NewsAPI key.")

        params = {"apiKey": key}
        if query:
            params["q"] = query
        if country or not query:
            params["country"] = country or "us"

        try:
            response = requests.get(self._ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        articles = [
            {
                "title": article.get("title"),
                "source": article.get("source", {}).get("name"),
                "url": article.get("url"),
            }
            for article in payload.get("articles", [])
        ]
        data = {"total_results": payload.get("totalResults", len(articles)), "articles": articles}
        return APIResponse(success=True, data=data)
