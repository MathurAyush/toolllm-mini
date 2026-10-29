# Live demo

**Double-click start_demo.bat, keep the black window open, and use the page that opens.**

To stop the server, close that window or double-click `stop_demo.bat`.

The website's demo page (`site/demo.html`) lets you type a question and watch
the agent retrieve APIs, call them and answer, step by step. A badge on the
page always shows which mode is active:

- **Live** (always the default): the page talks to the demo server, which runs
  the real retriever, agents and tools for every question. If the server is
  not running, a red "Backend offline" banner appears and the Run button is
  disabled; the page checks again every 3 seconds and goes live by itself as
  soon as the server is up.
- **Recorded demo** (only when you turn on "Use recorded demo"): the page
  replays runs that were recorded earlier with the same code
  (`results/demo_runs/`). Only the example questions have recordings, and
  nothing in this mode is live. The page never switches to it on its own.

## What start_demo.bat does

1. Creates the `venv` Python environment if it is missing and installs
   `requirements.txt` only when a package is missing.
2. Checks that `.env` exists and holds a Gemini key (the key is never shown).
3. If port 8000 is taken by an old demo server, stops it; if another program
   uses it, picks the next free port and says which one.
4. Starts the server, waits until `/api/health` answers, and opens
   `http://localhost:<port>/demo.html` in your default browser.
5. Keeps the window open with the server log.

Always use the page at `http://localhost:8000/demo.html`. Opening
`site/demo.html` as a file, or from another web server, cannot reach the API;
the page shows a banner saying so.

## Run it by hand

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
key" and a red banner explaining how to add it.

## GitHub Pages and hosting

GitHub Pages only serves static files, so on the published site live mode shows
the "Backend offline" banner, and visitors can only turn on the **recorded**
demo by hand. For live answers the server has to run somewhere:

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

When the daily cap is reached the page shows a "Demo limit reached" message.

## Refreshing the recorded runs

```bash
python scripts/record_demo_runs.py           # needs the key and network access
python scripts/export_site_data.py --demo-only
```

The example questions live in `data/demo_questions.json`.
