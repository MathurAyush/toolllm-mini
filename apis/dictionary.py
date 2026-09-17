from __future__ import annotations

import requests

from .base import APIResponse, BaseAPI


class DictionaryAPI(BaseAPI):
    """Free Dictionary API - Word Definition

    Description:
        Looks up an English word and returns its phonetic spelling, part
        of speech, and definitions, via the public Free Dictionary API.
        No authentication required.

    Required parameters:
        word (str): The English word to look up, e.g. "serendipity".

    Example response:
        {
            "word": "serendipity",
            "phonetic": "/ˌsɛr.ənˈdɪp.ɪ.ti/",
            "meanings": [
                {
                    "part_of_speech": "noun",
                    "definition": "The occurrence of events by chance in a happy way."
                }
            ]
        }
    """

    name = "dictionary"
    description = "Looks up the definition, phonetics, and part of speech for an English word."
    parameters = {"word": "English word to look up, e.g. 'serendipity'."}

    _ENDPOINT = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    def call(self, word: str) -> APIResponse:
        try:
            response = requests.get(self._ENDPOINT.format(word=word), timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        entry = payload[0] if payload else {}
        meanings = [
            {
                "part_of_speech": meaning.get("partOfSpeech"),
                "definition": meaning.get("definitions", [{}])[0].get("definition"),
            }
            for meaning in entry.get("meanings", [])
        ]
        data = {
            "word": entry.get("word", word),
            "phonetic": entry.get("phonetic", ""),
            "meanings": meanings,
        }
        return APIResponse(success=True, data=data)
