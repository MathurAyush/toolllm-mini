from __future__ import annotations

import re

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# (suffix, replacement), tried in order; the first one that fits wins.
_SUFFIXES = (
    ("ies", "y"),
    ("sses", "ss"),
    ("ing", ""),
    ("ed", ""),
    ("s", ""),
)
_KEEP_ENDINGS = ("ss", "us", "is")


def stem(word: str) -> str:
    """Very small suffix stripper, so that e.g. "converts" matches "convert"
    and "currencies" matches "currency". Words of three letters or fewer
    are left alone."""
    if len(word) <= 3 or word.endswith(_KEEP_ENDINGS):
        return word
    for suffix, replacement in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)] + replacement
    return word


def tokenize(text: str) -> list[str]:
    return [stem(token) for token in _TOKEN_PATTERN.findall(text.lower())]
