# ToolAgent

A scaled-down, original implementation inspired by the ToolLLM paper on
tool-use for language model agents. This project explores the core ideas
behind ToolLLM at a small scale: retrieving relevant APIs for a natural
language instruction, reasoning over multi-step tool calls with a ReAct
loop and a Depth-First Search-based Decision Tree (DFSDT) search
strategy, and evaluating the resulting behavior with pass-rate and
win-rate metrics.

## Project layout

- `apis/` — API wrapper definitions: 49 tools in `full_registry()`, 47
  in `keyless_registry()` (everything except OpenWeatherMap and
  NewsAPI, which need their own keys). Each API implements a small
  `BaseAPI` interface (`name`, `description`, `parameters`, `call`) so
  new tools can be registered without touching the rest of the system,
  and exposes a structured catalog entry through `registry_entry()`
  (name, description, category, typed parameters, required fields, and
  an example call with its response); `APIRegistry.catalog()` lists them
  all. The catalog covers:
  - offline examples: a calculator, a mock weather lookup, a small local
    search tool, and a unit converter;
  - the original public API wrappers: OpenWeatherMap, Frankfurter
    (currency exchange), Wikipedia summaries, NewsAPI, JokeAPI,
    Quotable, the Free Dictionary API, and REST Countries;
  - 37 more free public APIs, built on `PublicAPI` (`apis/http.py`),
    grouped by module: geocoding, forecasts, air quality, elevation,
    ZIP codes, IP geolocation and earthquakes (`geo.py`); world time,
    sunrise/sunset, public holidays and long weekends (`dates.py`);
    historical exchange rates and crypto prices (`finance.py`); Open
    Library book, ISBN and author lookup (`books.py`); recipes and
    cocktails (`food.py`); NASA APOD, near-earth asteroids, the ISS
    position and spaceflight news (`space.py`); cat and dog facts and
    dog photos (`animals.py`); random users, name-based age and
    nationality estimates, universities and GitHub profiles
    (`people.py`); and trivia, Pokemon, advice, colors, related words
    and Hacker News search (`fun.py`).

  A `PublicAPI` subclass declares typed `Param`s and implements one
  `fetch` (HTTP GET through `get_json`) and a `parse`. The base class
  validates and coerces arguments, applies a 10 s timeout, and turns
  timeouts, HTTP errors, non-JSON replies and unexpected payloads into a
  failed `APIResponse`. Each one also stores a recorded upstream
  response (`mock_payload`): with `offline=True`, or `TOOLLLM_OFFLINE=1`
  in the environment, it parses that payload instead of calling the
  network, which is how the tests run. A live failure is always reported
  as an error and never answered from the mock.
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
  Messages API) and `GeminiLLM` (backed by the Google Gen AI SDK) for
  real usage, and a deterministic `EchoLLM` for local development and
  tests — a `ReActAgent` implementing the reason/act loop, and a
  `DFSDTAgent` implementing a depth-first, branching search (capped at
  depth 4, breadth 3 and 20 model replies) over candidate reasoning
  paths with backtracking on failed actions. Both use native function
  calling: every candidate API is declared to the model as a function
  generated from its registry schema (`BaseAPI.function_schema()`), the
  model can only request a call, and the agent runs it and returns the
  real result as a function response. A question that needs no tool is
  answered directly and reported with `stop_reason="no_tool_needed"`.
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
  evaluation utilities. `tests/test_public_apis.py` has one offline test
  per public API, checks that every registry entry is complete and that
  each example call returns its documented example response, and checks
  that the retriever ranks each new tool in the top 3 for a typical
  request. The suite never touches the network.

## Getting started

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

To run the agents for real (`scripts/run_benchmark.py`,
`scripts/demo_retriever.py`), put an API key in a local `.env` file
(gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
BENCHMARK_PROVIDER=gemini  # or "anthropic"; picks which key run_benchmark.py uses
```

Every public API in the catalog works without a key. A few take an
optional free key from the same `.env` file for higher rate limits:
`NASA_API_KEY` (https://api.nasa.gov; falls back to the shared
`DEMO_KEY`), `GITHUB_TOKEN`, plus `OPENWEATHERMAP_API_KEY` and
`NEWSAPI_KEY` for the two key-only wrappers. `.env.example` lists them
all. Keys are read from the environment only, never passed as tool
arguments, and `.env` is never committed.

## Design notes

The retrieval, reasoning, and evaluation components are intentionally
decoupled: any `BaseAPI` implementation can be indexed by the
retriever, any `BaseLLM` implementation can drive either reasoning
loop, and any list of instructions can be scored with the evaluation
utilities. This makes it straightforward to swap in a real language
model client, add new APIs, or extend the evaluation harness without
restructuring the rest of the project.
