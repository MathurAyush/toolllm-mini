# ToolAgent

A scaled-down, original implementation inspired by the ToolLLM paper on
tool-use for language model agents. This project explores the core ideas
behind ToolLLM at a small scale: retrieving relevant APIs for a natural
language instruction, reasoning over multi-step tool calls with a ReAct
loop and a Depth-First Search-based Decision Tree (DFSDT) search
strategy, and evaluating the resulting behavior with pass-rate and
win-rate metrics.

## Project layout

- `apis/` — API wrapper definitions. Each API implements a small
  `BaseAPI` interface (`name`, `description`, `parameters`, `call`) so
  new tools can be registered without touching the rest of the system.
  Ships with a calculator, a mock weather lookup, and a small local
  search tool as offline examples, plus wrappers around eight free
  public APIs: OpenWeatherMap, Frankfurter (currency exchange),
  Wikipedia summaries, NewsAPI, JokeAPI, Quotable (quotes), the Free
  Dictionary API, and REST Countries. Each wrapper's docstring
  documents its name, description, required parameters, and an example
  response.
- `retriever/` — API retrieval logic. A lightweight TF-IDF based
  retriever ranks the registered APIs by relevance to a given
  instruction and returns the top-k candidates for the agent to
  consider.
- `agent/` — The reasoning loop. Includes a pluggable `BaseLLM`
  interface (with a deterministic `EchoLLM` for local development and
  tests), a `ReActAgent` implementing the Thought/Action/Observation
  loop, and a `DFSDTAgent` implementing a depth-first, branching search
  over candidate reasoning paths with backtracking on failed actions.
- `eval/` — Evaluation utilities: a pass-rate calculator, a pairwise
  win-rate calculator, and a simple keyword-based judge for scoring
  agent answers against expected outputs.
- `data/` — Sample instructions and expected keywords used for local
  evaluation runs.
- `tests/` — Unit tests covering the APIs, retriever, agent loops, and
  evaluation utilities.

## Getting started

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Design notes

The retrieval, reasoning, and evaluation components are intentionally
decoupled: any `BaseAPI` implementation can be indexed by the
retriever, any `BaseLLM` implementation can drive either reasoning
loop, and any list of instructions can be scored with the evaluation
utilities. This makes it straightforward to swap in a real language
model client, add new APIs, or extend the evaluation harness without
restructuring the rest of the project.
