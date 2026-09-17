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
"""


def build_prompt(instruction: str, api_descriptions: str, history: str) -> str:
    return (
        f"{REACT_SYSTEM_PROMPT.format(api_descriptions=api_descriptions)}\n"
        f"Instruction: {instruction}\n"
        f"{history}"
    )
