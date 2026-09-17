from __future__ import annotations

import re

ACTION_PATTERN = re.compile(r"Action:\s*(\w+)\[(.*)\]", re.DOTALL)
FINISH_PATTERN = re.compile(r"Finish\[(.*)\]", re.DOTALL)


def parse_action(response: str) -> re.Match | None:
    return ACTION_PATTERN.search(response)


def parse_finish(response: str) -> re.Match | None:
    return FINISH_PATTERN.search(response)


def parse_args(raw_args: str, api) -> dict:
    raw_args = raw_args.strip()
    if not raw_args:
        return {}
    if "=" in raw_args:
        kwargs = {}
        for part in raw_args.split(","):
            key, _, value = part.partition("=")
            kwargs[key.strip()] = value.strip().strip("'\"")
        return kwargs
    param_name = next(iter(api.parameters), "value")
    return {param_name: raw_args.strip("'\"")}
