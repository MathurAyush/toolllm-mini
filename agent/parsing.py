from __future__ import annotations

import inspect
import re

# One action per line; the argument list ends at the last "]" on that line,
# so text the model writes on later lines can never leak into the arguments.
ACTION_PATTERN = re.compile(r"Action:\s*(\w+)\[([^\n]*)\]")
FINISH_PATTERN = re.compile(r"Finish\[(.*)\]", re.DOTALL)
OBSERVATION_PATTERN = re.compile(r"^\s*Observation\s*:", re.MULTILINE)

# Split keyword arguments only at commas that start a new "key=" pair, so
# values such as "London,GB" or "2,000 + 5" stay in one piece.
_KWARG_SPLIT = re.compile(r",\s*(?=[A-Za-z_]\w*\s*=)")


def truncate_at_observation(response: str) -> str:
    """Drops everything from the first "Observation:" line onwards.

    Observations must come from real tool calls. A model that writes its own
    Observation (and often a Finish after it) in the same reply is guessing
    the tool's result, so that part of the reply is discarded.
    """
    match = OBSERVATION_PATTERN.search(response)
    return response[: match.start()].rstrip() if match else response


def parse_action(response: str) -> re.Match | None:
    return ACTION_PATTERN.search(response)


def parse_finish(response: str) -> re.Match | None:
    return FINISH_PATTERN.search(response)


def parse_step(response: str) -> tuple[re.Match | None, re.Match | None]:
    """Returns (action_match, finish_match), at most one of them set.

    The reply is cut at the first Observation line first. If it still holds
    both an Action and a Finish, whichever comes first wins: an Action before
    a Finish means the answer was written before the tool was run.
    """
    response = truncate_at_observation(response)
    action_match = parse_action(response)
    finish_match = parse_finish(response)
    if finish_match and (action_match is None or finish_match.start() < action_match.start()):
        return None, finish_match
    return action_match, None


def _strip_quotes(value: str) -> str:
    return value.strip().strip("'\"")


def _required_params(api) -> list[str]:
    try:
        signature = inspect.signature(api.call)
    except (TypeError, ValueError):
        return []
    return [
        name
        for name, param in signature.parameters.items()
        if param.default is inspect.Parameter.empty
        and param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY)
    ]


def parse_args(raw_args: str, api) -> dict:
    raw_args = raw_args.strip()
    if not raw_args:
        return {}

    if re.match(r"[A-Za-z_]\w*\s*=", raw_args):
        kwargs = {}
        for part in _KWARG_SPLIT.split(raw_args):
            key, _, value = part.partition("=")
            kwargs[key.strip()] = _strip_quotes(value)
        return kwargs

    param_names = list(api.parameters)
    # Positional "USD, EUR, 100" maps onto the parameters in order, but only
    # for tools that need more than one argument; for single-argument tools a
    # comma belongs to the value (e.g. "London,GB" or a search query).
    if len(_required_params(api)) > 1:
        parts = [_strip_quotes(p) for p in raw_args.split(",")]
        if len(parts) <= len(param_names):
            return dict(zip(param_names, parts))

    param_name = param_names[0] if param_names else "value"
    return {param_name: _strip_quotes(raw_args)}
