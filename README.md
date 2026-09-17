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
- `retriever/` — API retrieval logic. `APIRetriever` ranks registered
  APIs by relevance to a given instruction and returns the top-k
  candidates for the agent to consider, using a pluggable text
  embedder: `TfidfEmbedder` (default) or `SentenceTransformerEmbedder`
  for semantic, embedding-based retrieval. `KeywordMatchRetriever`
  provides a no-embeddings, keyword-overlap baseline for comparison.
  `scripts/demo_retriever.py` compares the keyword baseline against the
  semantic retriever on the sample instructions.
- `agent/` — The reasoning loop. Includes a pluggable `BaseLLM`
  interface — `AnthropicLLM` (the default, backed by the Anthropic
  Messages API) for real usage, and a deterministic `EchoLLM` for local
  development and tests — a `ReActAgent` implementing the
  Thought/Action/Observation loop, and a `DFSDTAgent` implementing a
  depth-first, branching search (capped at depth 4, breadth 3) over
  candidate reasoning paths with backtracking on failed or unproductive
  actions.
- `eval/` — Evaluation utilities: a keyword-based `judge_pass` for
  scoring answers against expected keywords, and an `LLMJudge` that uses
  a language model to grade a single answer as Pass/Fail/Unsure
  (`run_pass_rate_eval`) or to pick the better of two candidate
  solutions to the same instruction (`run_win_rate_eval`), aggregating
  into a pass rate / win rate and saving the per-instruction verdicts
  and rationales to a CSV file.
- `data/` — Sample instructions and expected keywords for quick local
  checks, plus `benchmark_instructions.json`: 19 test instructions of
  varying complexity (`easy`/`medium`/`hard`, needing 1-3 APIs) used by
  `scripts/run_benchmark.py`.
- `results/` — Output of `scripts/run_benchmark.py`: a per-instruction
  CSV (`benchmark_results.csv`), a ReAct-vs-DFSDT pass-rate comparison
  table (`comparison_table.md`), and a bar chart
  (`pass_rate_comparison.png`).
- `tests/` — Unit tests covering the APIs, retriever, agent loops, and
  evaluation utilities.

## Getting started

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

To run the agents for real (`AnthropicLLM`, `scripts/run_benchmark.py`,
`scripts/demo_retriever.py`), put an API key in a local `.env` file
(gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Design notes

The retrieval, reasoning, and evaluation components are intentionally
decoupled: any `BaseAPI` implementation can be indexed by the
retriever, any `BaseLLM` implementation can drive either reasoning
loop, and any list of instructions can be scored with the evaluation
utilities. This makes it straightforward to swap in a real language
model client, add new APIs, or extend the evaluation harness without
restructuring the rest of the project.
