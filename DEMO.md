# Live demo

The website's demo page (`site/demo.html`) lets you type a question and watch
the agent retrieve APIs, call them and answer, step by step. It runs in one of
two modes, and a badge on the page always shows which one is active:

- **Live**: the page talks to the demo server, which runs the real retriever,
  agents and tools for every question.
- **Recorded demo**: when no server is reachable, the page replays runs that
  were recorded earlier with the same code (`results/demo_runs/`). Only the
  example questions can be replayed, and nothing in this mode is live.

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your key in .env (see below)
python -m uvicorn server.app:app --port 8000
```

Open <http://localhost:8000/demo.html>. The same command serves the whole
website and the API, so nothing else needs to run.

## The model key

The server reads the key from `.env` in the project root:

```
GEMINI_API_KEY=your-key-here
```

The key stays on the server. It is never sent to the browser, and error
messages shown on the page never include it, stack traces or file paths.
If the key is missing the page still loads, shows "Backend online · no model
key", and falls back to the recorded demo.

## GitHub Pages and hosting

GitHub Pages only serves static files, so the published site can only show the
**recorded** mode. For live answers the server has to run somewhere:

- locally, with the command above, or
- on a host such as Render or Railway, with the start command
  `python -m uvicorn server.app:app --host 0.0.0.0 --port $PORT` and
  `GEMINI_API_KEY` stored as an environment variable in the host's settings
  (never committed to the repository).

To point the published page at a deployed server, open **Settings** on the demo
page and enter the server's address; it is saved in your browser. The server
only accepts requests from localhost and the site's own origin. Add other
origins with `DEMO_ALLOWED_ORIGINS`, and set `DEMO_TRUST_PROXY=1` behind a proxy
so the per-visitor rate limit sees real client addresses.

## Limits

| Setting | Default | Environment variable |
| --- | --- | --- |
| Question length | 300 characters | – |
| Tool calls per question | 8 | – |
| Runs per visitor per minute | 6 | `DEMO_RATE_PER_MINUTE` |
| Runs per day, all visitors | 300 | `DEMO_DAILY_CAP` |
| Runs at the same time | 4 | `DEMO_MAX_CONCURRENT` |

When the daily cap is reached the page shows a "Demo limit reached" message
and offers the recorded demo.

## Refreshing the recorded runs

```bash
python scripts/record_demo_runs.py           # needs the key and network access
python scripts/export_site_data.py --demo-only
```

The example questions live in `data/demo_questions.json`.
