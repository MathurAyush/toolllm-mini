from __future__ import annotations

from typing import Callable

# Optional progress callback for the agents: called as handler(kind, data)
# while a run is in progress, so a UI can show each step as it happens.
#
#   "step"      a tool call was executed: thought, call, result, observation
#               (and node, for DFSDT)
#   "node"      DFSDT sampled a model reply: id, parent, depth, tools
#   "backtrack" DFSDT abandoned a node: node, reason ("tool_error",
#               "empty_reply" or "dead_end")
#   "answer"    the final answer: text (and node, for DFSDT)
EventHandler = Callable[[str, dict], None]


def emit(handler: EventHandler | None, kind: str, **data) -> None:
    if handler is not None:
        handler(kind, data)
