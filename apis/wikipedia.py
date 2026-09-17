from __future__ import annotations

from urllib.parse import quote

import requests

from .base import APIResponse, BaseAPI


class WikipediaSummaryAPI(BaseAPI):
    """Wikipedia - Page Summary

    Description:
        Fetches a short plain-text summary and metadata for a Wikipedia
        article using the public Wikimedia REST API. No authentication
        required.

    Required parameters:
        title (str): Exact or close title of the Wikipedia page, e.g.
            "Python (programming language)".

    Example response:
        {
            "title": "Python (programming language)",
            "extract": "Python is a high-level, general-purpose programming language...",
            "url": "https://en.wikipedia.org/wiki/Python_(programming_language)"
        }
    """

    name = "wikipedia_summary"
    description = "Fetches a short summary of a Wikipedia article by title."
    parameters = {"title": "Title of the Wikipedia page, e.g. 'Python (programming language)'."}

    _ENDPOINT = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

    def call(self, title: str) -> APIResponse:
        try:
            response = requests.get(self._ENDPOINT.format(title=quote(title)), timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        data = {
            "title": payload.get("title", title),
            "extract": payload.get("extract", ""),
            "url": payload.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
        return APIResponse(success=True, data=data)
