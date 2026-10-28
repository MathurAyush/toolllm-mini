"""Runs one question through the retriever and a ReAct or DFSDT agent for
the website's live demo, and turns the agent's progress events into the
JSON the page shows: retrieved tools, steps, the DFSDT search tree and
the final answer.

Every run is bounded: a deadline, a cap on model replies and a cap on
tool calls. Tool output is cleaned before it leaves the server, so no
configured secret or local file path can reach the browser.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from agent.dfsdt import DFSDTAgent
from agent.llm import BaseLLM, LLMResponse, Message, ModelTurn
from agent.react import ReActAgent
from apis.base import APIResponse, BaseAPI
from apis.registry import APIRegistry
from retriever.retriever import APIRetriever

log = logging.getLogger("server")

STRATEGIES = ("react", "dfsdt")

# Sends one event to the browser: sink(event_name, payload).
Sink = Callable[[str, dict], None]


class DemoError(Exception):
    """An error with a message that is safe and friendly to show to the
    visitor, and the HTTP status to send it with."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def payload(self) -> dict:
        return {"code": self.code, "message": self.message}


class RunCancelled(Exception):
    """The visitor cancelled the run or closed the page."""


@dataclass(frozen=True)
class Limits:
    max_question_chars: int = 300
    max_top_k: int = 10
    react_max_replies: int = 6
    dfsdt_max_replies: int = 10
    max_tool_calls: int = 8
    run_timeout: float = 90.0
    max_observation_chars: int = 4000


@dataclass(frozen=True)
class RunParams:
    question: str
    strategy: str
    top_k: int


def validate(question: Any, strategy: Any, top_k: Any, limits: Limits) -> RunParams:
    if not isinstance(question, str) or not question.strip():
        raise DemoError("empty_question", "Please type a question first.")
    question = question.strip()
    if len(question) > limits.max_question_chars:
        raise DemoError(
            "question_too_long",
            f"Questions are limited to {limits.max_question_chars} characters (this one has {len(question)}).",
        )
    strategy = str(strategy).strip().lower() if strategy is not None else ""
    if strategy not in STRATEGIES:
        raise DemoError("invalid_strategy", 'The strategy must be "react" or "dfsdt".')
    try:
        k = int(top_k)
        if isinstance(top_k, float) and not top_k.is_integer():
            raise ValueError
    except (TypeError, ValueError):
        k = 0
    if not 1 <= k <= limits.max_top_k:
        raise DemoError("invalid_top_k", f"top_k must be a whole number from 1 to {limits.max_top_k}.")
    return RunParams(question, strategy, k)


# ------------------------------------------------------------------ cleaning

_KEY_IN_URL = re.compile(r"(?i)\b(api_?key|key|token|access_token|appid)=[^&\s'\"]+")
# A drive path, or an absolute Unix path that is not part of a URL.
_LOCAL_PATH = re.compile(r"(?i)(?:\b[a-z]:\\|(?<![\w.:/-])/(?:home|users|usr|opt|var|tmp|etc|app|srv)/)[^\s'\"]*")
_SECRET_NAME = re.compile(r"(?i)(key|token|secret|password)")


def _secrets() -> list[str]:
    return [v for k, v in os.environ.items() if _SECRET_NAME.search(k) and v and len(v) >= 8]


def scrub(text: str) -> str:
    """Removes configured secrets, keys in URLs and local file paths."""
    for secret in _secrets():
        text = text.replace(secret, "***")
    text = _KEY_IN_URL.sub(lambda m: f"{m.group(1)}=***", text)
    return _LOCAL_PATH.sub("<path>", text)


def clean(value: Any) -> Any:
    """Plain, finite JSON with every string scrubbed."""
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return scrub(str(value))


def _observation(response: dict, max_chars: int) -> Any:
    """The tool's result (or error message), cut down to a size the page
    can show."""
    value = clean(response.get("result") if "result" in response else response.get("error", ""))
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return value


def _summary(description: str, limit: int = 140) -> str:
    first = description.split(". ")[0].rstrip(".") + "."
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


# ------------------------------------------------------------------ budget


class _Budget:
    """The stop conditions shared by one run: a deadline, the visitor
    cancelling, and the tool-call cap."""

    def __init__(self, limits: Limits, cancel: threading.Event | None) -> None:
        self.limits = limits
        self.cancel = cancel or threading.Event()
        self.deadline = time.monotonic() + limits.run_timeout
        self.tool_calls = 0

    def stopped(self) -> bool:
        return self.cancel.is_set() or time.monotonic() > self.deadline

    def check(self) -> None:
        if self.cancel.is_set():
            raise RunCancelled()
        if time.monotonic() > self.deadline:
            raise DemoError("timeout", "The agent took too long to answer, so the run was stopped. Please try again.", 504)


class _GuardedLLM(BaseLLM):
    """Checks the budget before every model request."""

    def __init__(self, llm: BaseLLM, budget: _Budget) -> None:
        self._llm = llm
        self._budget = budget

    def generate(self, prompt: str) -> LLMResponse:
        self._budget.check()
        return self._llm.generate(prompt)

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> ModelTurn:
        self._budget.check()
        return self._llm.chat(system, messages, tools)


class _BudgetedAPI:
    """Stands in for an API when the agent executes a call: counts the call
    against the run's cap. Reports a stop as a failed call, because the
    agent turns any exception from a tool into an error result."""

    def __init__(self, api: BaseAPI, budget: _Budget) -> None:
        self._api = api
        self._budget = budget
        self.name = api.name

    def function_schema(self) -> dict:
        return self._api.function_schema()

    def call(self, **kwargs: Any) -> APIResponse:
        if self._budget.stopped():
            return APIResponse(success=False, error="The run was stopped.")
        if self._budget.tool_calls >= self._budget.limits.max_tool_calls:
            return APIResponse(
                success=False,
                error=f"The demo allows at most {self._budget.limits.max_tool_calls} tool calls per question.",
            )
        self._budget.tool_calls += 1
        return self._api.call(**kwargs)


class _BudgetedRegistry:
    def __init__(self, registry: APIRegistry, budget: _Budget) -> None:
        self._registry = registry
        self._budget = budget

    def get(self, name: str) -> _BudgetedAPI | None:
        api = self._registry.get(name)
        return None if api is None else _BudgetedAPI(api, self._budget)


# ------------------------------------------------------------------ events

_BACKTRACK_MESSAGES = {
    "tool_error": "A tool call failed, so this branch is dropped and another reply is tried.",
    "empty_reply": "The model returned an empty reply, so another reply is tried.",
    "dead_end": "Nothing below this branch reached an answer, so the search backtracks.",
}


class _Recorder:
    """Turns agent events into the demo's steps and tree, and forwards each
    one to the sink as it happens."""

    def __init__(self, sink: Sink | None, limits: Limits) -> None:
        self._sink = sink
        self._limits = limits
        self.steps: list[dict] = []
        self.nodes: dict[int, dict] = {0: {"id": 0, "parent": None, "depth": 0, "tools": [], "status": "root"}}
        self.answer_node: int | None = None

    def send(self, event: str, payload: dict) -> None:
        if self._sink is not None:
            self._sink(event, payload)

    def __call__(self, kind: str, data: dict) -> None:
        if kind == "step":
            call, result = data["call"], data["result"]
            step = {
                "index": len(self.steps) + 1,
                "node": data.get("node"),
                "thought": scrub(data["thought"]),
                "tool": call.name,
                "arguments": clean(call.args),
                "observation": _observation(result.response, self._limits.max_observation_chars),
                "status": "error" if result.is_error else "ok",
                "backtracked": False,
            }
            self.steps.append(step)
            self.send("step", step)
        elif kind == "node":
            node = {
                "id": data["id"],
                "parent": data["parent"],
                "depth": data["depth"],
                "tools": list(data["tools"]),
                "status": "open",
            }
            self.nodes[node["id"]] = node
            self.send("node", dict(node))
        elif kind == "backtrack":
            node_id = data["node"]
            reason = data["reason"]
            self.nodes[node_id]["status"] = "dead_end" if reason == "dead_end" else "error"
            marked = []
            for step in self.steps:
                if step["node"] == node_id:
                    step["backtracked"] = True
                    marked.append(step["index"])
            self.send(
                "backtrack",
                {"node": node_id, "reason": reason, "steps": marked, "message": _BACKTRACK_MESSAGES[reason]},
            )
        elif kind == "answer":
            node_id = data.get("node")
            if node_id is not None:
                self.nodes[node_id]["status"] = "answer"
                self.answer_node = node_id
            self.send("answer", {"text": scrub(data["text"])})

    def tree(self) -> dict:
        path, node_id = [], self.answer_node
        while node_id is not None:
            path.append(node_id)
            node_id = self.nodes[node_id]["parent"]
        path.reverse()
        on_path = set(path)
        for node in self.nodes.values():
            if node["status"] == "open":
                node["status"] = "ok" if node["id"] in on_path else "dead_end"
        nodes = [dict(node, chosen=node["id"] in on_path) for node in self.nodes.values()]
        return {"nodes": nodes, "chosen_path": path, "explored": len(nodes) - 1}


# ------------------------------------------------------------------ run


def run_question(
    params: RunParams,
    *,
    registry: APIRegistry,
    retriever: APIRetriever,
    llm: BaseLLM,
    model: str,
    limits: Limits,
    sink: Sink | None = None,
    cancel: threading.Event | None = None,
) -> dict:
    """Retrieves candidate tools, runs the agent and returns the full run.
    With a `sink`, sends "retrieved", "node", "step", "backtrack",
    "answer" and finally "done" (the returned run) as they happen."""
    budget = _Budget(limits, cancel)
    started = time.perf_counter()
    recorder = _Recorder(sink, limits)

    hits = retriever.retrieve(params.question, top_k=params.top_k)
    retrieved = [
        {
            "name": hit.api.name,
            "score": round(hit.score, 4),
            "category": hit.api.category,
            "description": _summary(hit.api.description),
        }
        for hit in hits
    ]
    recorder.send(
        "retrieved",
        {"strategy": params.strategy, "model": model, "top_k": params.top_k, "retrieved_tools": retrieved},
    )

    guarded = _GuardedLLM(llm, budget)
    tools = _BudgetedRegistry(registry, budget)
    if params.strategy == "dfsdt":
        agent = DFSDTAgent(registry=tools, llm=guarded, max_steps=limits.dfsdt_max_replies, on_event=recorder)
    else:
        agent = ReActAgent(registry=tools, llm=guarded, max_steps=limits.react_max_replies, on_event=recorder)
    result = agent.run(params.question, candidate_apis=[hit.api for hit in hits])
    budget.check()  # a run cancelled during its last tool call ends here

    steps = recorder.steps
    called = []
    for step in steps:
        if step["status"] == "ok" and step["tool"] not in called:
            called.append(step["tool"])
    run = {
        "question": params.question,
        "strategy": params.strategy,
        "top_k": params.top_k,
        "model": model,
        "retrieved_tools": retrieved,
        "steps": steps,
        "tools_called": called,
        "final_answer": scrub(result.answer) if result.answer else None,
        "success": result.success,
        "stop_reason": result.stop_reason,
        "num_steps": len(steps) + (1 if result.answer else 0),
        "num_tool_calls": len(steps),
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "tree": recorder.tree() if params.strategy == "dfsdt" else None,
    }
    recorder.send("done", run)
    return run


_RATE_LIMIT = re.compile(r"\b429\b|rate.?limit|resource.?exhausted|quota", re.I)
_TIMEOUT = re.compile(r"time(d)?.?out|deadline", re.I)
_CREDENTIALS = re.compile(r"api.?key|credential|permission.?denied|unauthori[sz]ed|\b40[13]\b", re.I)


def friendly_error(exc: BaseException) -> DemoError:
    """Maps any failure to a message that is safe to show: never the
    exception text, a stack trace or a path. The details go to the log."""
    if isinstance(exc, DemoError):
        return exc
    if isinstance(exc, RunCancelled):
        return DemoError("cancelled", "The run was cancelled.", 499)
    log.exception("Agent run failed", exc_info=exc)
    text = f"{type(exc).__name__} {exc}"
    if _RATE_LIMIT.search(text):
        return DemoError(
            "model_rate_limited",
            "The language model is getting too many requests right now. Please wait a minute and try again.",
            503,
        )
    if _TIMEOUT.search(text):
        return DemoError("timeout", "The language model took too long to respond. Please try again.", 504)
    if _CREDENTIALS.search(text):
        return DemoError(
            "not_configured",
            "The live demo is not set up on this server (the model key is missing or invalid). "
            "The recorded demo still works.",
            503,
        )
    return DemoError("agent_error", "Something went wrong while running the agent. Please try again.", 500)
