from __future__ import annotations

from .base import APIResponse, BaseAPI


class SearchAPI(BaseAPI):
    name = "search"
    description = "Searches a small local knowledge base and returns matching snippets."
    parameters = {"query": "Free-text search query."}

    _DOCUMENTS = [
        "The Eiffel Tower is located in Paris, France.",
        "Mount Fuji is the tallest mountain in Japan.",
        "The Great Wall of China stretches over 21,000 kilometers.",
        "Python is a general-purpose programming language created by Guido van Rossum.",
    ]

    def call(self, query: str) -> APIResponse:
        terms = {t.lower() for t in query.split() if t}
        matches = [
            doc
            for doc in self._DOCUMENTS
            if terms & {w.strip(".,").lower() for w in doc.split()}
        ]
        if not matches:
            return APIResponse(success=False, error="No matching documents found.")
        return APIResponse(success=True, data=matches)
