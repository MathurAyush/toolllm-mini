from __future__ import annotations

import json

from apis.base import BaseAPI
from apis.registry import APIRegistry

from .llm import ModelTurn, ToolCall, ToolResult


def function_declarations(apis: list[BaseAPI]) -> list[dict]:
    return [api.function_schema() for api in apis]


def _jsonable(value):
    """Round-trips through JSON so the function response only holds plain
    JSON values, whatever the API returned."""
    return json.loads(json.dumps(value, default=str))


def _check_args(api: BaseAPI, args: dict) -> str | None:
    schema = api.function_schema()["parameters"]
    unknown = sorted(set(args) - set(schema["properties"]))
    if unknown:
        return f"unknown argument(s) {', '.join(unknown)} for '{api.name}'"
    missing = [name for name in schema["required"] if name not in args]
    if missing:
        return f"missing required argument(s) {', '.join(missing)} for '{api.name}'"
    return None


def execute_tool_call(call: ToolCall, registry: APIRegistry, allowed: set[str]) -> tuple[ToolResult, str]:
    """Runs a tool call the model requested and returns the real result, as
    the function response for the model and as an observation string for the
    trace. This is the only place tool results come from."""
    api = registry.get(call.name) if call.name in allowed else None
    if api is None:
        error = f"unknown tool '{call.name}'"
    else:
        error = _check_args(api, call.args)
        if error is None:
            try:
                result = api.call(**call.args)
            except Exception as exc:  # noqa: BLE001 - reported back to the model as an error result
                error = str(exc) or type(exc).__name__
            else:
                if result.success:
                    data = _jsonable(result.data)
                    return ToolResult(call=call, response={"result": data}), str(result.data)
                error = result.error or "the tool reported a failure"

    return ToolResult(call=call, response={"error": error}, is_error=True), f"Error: {error}"


def describe_call(call: ToolCall) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in call.args.items())
    return f"Action: {call.name}({args})"


def turn_thought(turn: ModelTurn, call: ToolCall) -> str:
    """The model's text accompanying a tool call, attached to the turn's
    first call only."""
    return turn.text.strip() if call is turn.tool_calls[0] else ""


def describe_turn(turn: ModelTurn, call: ToolCall) -> str:
    """Trace text for one tool call: the model's accompanying text (if any,
    and only on the turn's first call) followed by the requested action."""
    text = turn_thought(turn, call)
    return f"{text}\n{describe_call(call)}" if text else describe_call(call)


def finish_text(answer: str, used_tools: bool) -> str:
    return f"Finish[{answer}]" if used_tools else f"No tool needed.\nFinish[{answer}]"


def tool_names(apis: list[BaseAPI]) -> set[str]:
    return {api.name for api in apis}
