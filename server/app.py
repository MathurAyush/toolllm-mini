"""HTTP server for the website's live demo, and the website itself.

Usage:
    python -m uvicorn server.app:app --port 8000

then open http://localhost:8000/demo.html. Serves the static site in site/
and a small JSON API that runs the same retriever, agents and tools as
app.py:

    GET  /api/health         status and model name
    GET  /api/tools          every tool the agent can call
    POST /api/run            {question, strategy, top_k} -> the whole run
    GET  /api/run/stream     same inputs as query parameters, sent as
                             Server-Sent Events while the run happens

The model key is read from .env (GEMINI_API_KEY) on the server and never
sent to the browser. Limits for a public deployment are set with the
DEMO_* environment variables listed in Settings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

from agent.factory import build_llm, configured_model
from agent.llm import BaseLLM
from apis.registry import APIRegistry, keyless_registry
from retriever.retriever import APIRetriever

from .limits import RateLimiter
from .runner import DemoError, Limits, RunParams, friendly_error, run_question, validate

log = logging.getLogger("server")

_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = _ROOT / "site"

# The published site, plus any local port (python -m http.server, etc.).
_DEFAULT_ORIGINS = "https://mathurayush.github.io"
_LOCAL_ORIGIN = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
_KEY_ENV = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """DEMO_RATE_PER_MINUTE   runs per visitor per minute (default 6)
    DEMO_DAILY_CAP          runs per UTC day, all visitors (default 300)
    DEMO_MAX_CONCURRENT     runs at the same time (default 4)
    DEMO_ALLOWED_ORIGINS    comma-separated extra origins for CORS
    DEMO_TRUST_PROXY        1 behind a proxy that sets X-Forwarded-For
    """

    rate_per_minute: int = 6
    daily_cap: int = 300
    max_concurrent: int = 4
    allowed_origins: tuple[str, ...] = (_DEFAULT_ORIGINS,)
    trust_proxy: bool = False
    limits: Limits = field(default_factory=Limits)

    @classmethod
    def from_env(cls) -> "Settings":
        extra = [o.strip().rstrip("/") for o in os.environ.get("DEMO_ALLOWED_ORIGINS", "").split(",") if o.strip()]
        return cls(
            rate_per_minute=_env_int("DEMO_RATE_PER_MINUTE", 6),
            daily_cap=_env_int("DEMO_DAILY_CAP", 300),
            max_concurrent=_env_int("DEMO_MAX_CONCURRENT", 4),
            allowed_origins=(_DEFAULT_ORIGINS, *extra),
            trust_proxy=os.environ.get("DEMO_TRUST_PROXY", "").strip().lower() in {"1", "true", "yes"},
        )


class UTF8JSONResponse(JSONResponse):
    """JSON with non-ASCII text kept as is (e.g. the degree sign) and the
    charset stated."""

    media_type = "application/json; charset=utf-8"


def _error(err: DemoError) -> UTF8JSONResponse:
    return UTF8JSONResponse({"error": err.payload()}, status_code=err.status)


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _default_llm() -> BaseLLM:
    # Few retries: a visitor is waiting, and the run has its own deadline.
    return build_llm(max_retries=2)[0]


def _key_configured() -> bool:
    try:
        provider, _ = configured_model()
    except ValueError:
        return False
    return bool(os.environ.get(_KEY_ENV[provider]))


def create_app(
    settings: Settings | None = None,
    registry: APIRegistry | None = None,
    llm_factory: Callable[[], BaseLLM] | None = None,
    model_name: str | None = None,
    serve_site: bool = True,
) -> FastAPI:
    """Builds the app. Tests pass their own registry and a scripted LLM."""
    settings = settings or Settings.from_env()
    registry = registry or keyless_registry()
    retriever = APIRetriever(apis=registry.all())
    if llm_factory is None:
        llm_factory = _default_llm
        ready = _key_configured
        try:
            model = configured_model()[1]
        except ValueError:
            model = "not configured"
    else:
        ready = lambda: True  # noqa: E731
        model = model_name or "test-model"
    limiter = RateLimiter(settings.rate_per_minute, settings.daily_cap)
    slots = threading.BoundedSemaphore(settings.max_concurrent)
    limits = settings.limits

    app = FastAPI(title="ToolAgent demo", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_origin_regex=_LOCAL_ORIGIN,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        # Lets the published site (a public origin) reach a server running on
        # the visitor's own computer, which browsers otherwise block.
        allow_private_network=True,
    )

    @app.exception_handler(DemoError)
    async def _demo_error(request: Request, exc: DemoError):
        return _error(exc)

    @app.exception_handler(RequestValidationError)
    async def _bad_request(request: Request, exc: RequestValidationError):
        return _error(DemoError("invalid_request", "The request could not be read. Send JSON with a question."))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _error(DemoError("not_found", "Not found.", 404))
        if exc.status_code == 405:
            return _error(DemoError("method_not_allowed", "That method is not allowed here.", 405))
        return _error(DemoError("http_error", "The request could not be completed.", exc.status_code))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        return _error(friendly_error(exc))

    def visitor(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if settings.trust_proxy and forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def admit(request: Request) -> None:
        """Takes a run slot and counts the run against the limits, or
        raises a DemoError. The caller releases the slot."""
        if not slots.acquire(blocking=False):
            raise DemoError(
                "busy", "The demo is busy answering other questions. Please try again in a few seconds.", 503
            )
        try:
            limiter.hit(visitor(request))
        except DemoError:
            slots.release()
            raise

    def execute(params: RunParams, sink=None, cancel=None) -> dict:
        return run_question(
            params,
            registry=registry,
            retriever=retriever,
            llm=llm_factory(),
            model=model,
            limits=limits,
            sink=sink,
            cancel=cancel,
        )

    @app.get("/api/health")
    def health():
        return UTF8JSONResponse(
            {
                "status": "ok",
                "model": model,
                "live": ready(),
                "limits": {
                    "max_question_chars": limits.max_question_chars,
                    "max_top_k": limits.max_top_k,
                    "max_tool_calls": limits.max_tool_calls,
                    "runs_left_today": limiter.remaining_today(),
                },
            }
        )

    @app.get("/api/tools")
    def tools():
        return UTF8JSONResponse(
            {
                "tools": [
                    {
                        "name": entry["name"],
                        "description": entry["description"],
                        "parameters": entry["parameters"],
                        "required": entry["required"],
                        "category": entry["category"],
                    }
                    for entry in registry.catalog()
                ]
            }
        )

    @app.post("/api/run")
    async def run(request: Request):
        try:
            body: Any = await request.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise DemoError("invalid_request", "Send a JSON object with a question, a strategy and top_k.")
        params = validate(body.get("question"), body.get("strategy", "react"), body.get("top_k", 5), limits)
        admit(request)
        try:
            return UTF8JSONResponse(await run_in_threadpool(execute, params))
        except Exception as exc:  # noqa: BLE001 - shown as a friendly message
            return _error(friendly_error(exc))
        finally:
            slots.release()

    @app.get("/api/run/stream")
    async def run_stream(request: Request, question: str = "", strategy: str = "react", top_k: str = "5"):
        params = validate(question, strategy, top_k, limits)
        admit(request)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        cancel = threading.Event()

        def put(item) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, item)
            except RuntimeError:  # the event loop is gone: nobody is listening
                cancel.set()

        def work() -> None:
            try:
                execute(params, sink=lambda event, payload: put((event, payload)), cancel=cancel)
            except Exception as exc:  # noqa: BLE001 - sent as an "error" event
                err = friendly_error(exc)
                if err.code != "cancelled":
                    put(("error", err.payload()))
            finally:
                slots.release()
                put(None)

        loop.run_in_executor(None, work)

        async def events():
            try:
                yield ": stream open\n\n"
                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
                        continue
                    if item is None:
                        break
                    yield _sse(*item)
            finally:
                cancel.set()  # the visitor left or cancelled: stop the agent

        return StreamingResponse(
            events(),
            media_type="text/event-stream; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.api_route("/api/{rest:path}", methods=["GET", "POST"])
    def api_not_found(rest: str):
        raise DemoError("not_found", "There is no such API endpoint.", 404)

    if serve_site and SITE_DIR.is_dir():
        app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")

    return app


app = create_app()
