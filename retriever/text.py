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

# Function words that carry no signal about which tool a request needs. With
# dozens of tools, matches on "what", "is" or "me" otherwise decide rankings.
STOP_WORDS = frozenset(
    """
    a an the and or but if then than so of to in on at by for from with without into onto
    as is are was were be been being am do does did done can could will would shall should
    may might must i me my mine we our you your he him his she her it its they them their
    this that these those there here what which who whom whose when where why how
    all any some each every no not only also just very too more most much many such
    about up down out over under again once now right please tell give show get let make
    want need like know s t
    """.split()
)


def stem(word: str) -> str:
    """Very small suffix stripper, so that e.g. "converts" matches "convert",
    "currencies" matches "currency" and "divided" matches "divide". Words of
    three letters or fewer are left alone."""
    if len(word) <= 3 or word.endswith(_KEEP_ENDINGS):
        return word
    for suffix, replacement in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)] + replacement
            break
    # A final "e" is dropped so that "divide" and "divided" share a stem.
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    return [stem(token) for token in _TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS]
