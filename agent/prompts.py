from __future__ import annotations

REACT_SYSTEM_PROMPT = """You are an assistant that solves tasks by interleaving Thought,
Action, and Observation steps, in the style of ReAct. Available actions:

{api_descriptions}

Use the format:
Thought: reasoning about what to do next
Action: api_name[arguments]
Observation: result of the action
...
Finish[final answer]

Write at most one Action per reply and stop right after it. Never write an
Observation line yourself: the system runs the action and adds the real
Observation. Only use Finish once the observations contain what you need.
"""


def build_prompt(instruction: str, api_descriptions: str, history: str) -> str:
    return (
        f"{REACT_SYSTEM_PROMPT.format(api_descriptions=api_descriptions)}\n"
        f"Instruction: {instruction}\n"
        f"{history}"
    )
