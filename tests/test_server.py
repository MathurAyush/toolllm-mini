import json

import pytest
from fastapi.testclient import TestClient

from agent.llm import EchoLLM, ModelTurn, ToolCall
from apis.base import APIResponse, BaseAPI
from apis.registry import APIRegistry
from server.app import Settings, create_app
from server.limits import RateLimiter
from server.runner import DemoError, Limits, scrub


class FakeGeocode(BaseAPI):
    name = "geocode"
    description = "Finds the latitude and longitude of a city or place."
    parameters = {"place": "Place name."}
    category = "geo"

    def __init__(self):
        self.calls = []

    def call(self, place: str) -> APIResponse:
        self.calls.append(place)
        return APIResponse(success=True, data={"name": place, "latitude": 38.72, "longitude": -9.14})


class FakeWeather(BaseAPI):
    name = "weather_forecast"
    description = "Weather forecast temperature for a latitude and longitude."
    parameters = {"latitude": "Latitude.", "longitude": "Longitude."}
    category = "weather"

    def call(self, latitude: float, longitude: float) -> APIResponse:
        return APIResponse(success=True, data={"temperature": "21 °C"})


class BrokenElevation(BaseAPI):
    name = "elevation"
    description = "Elevation above sea level of a place, in metres."
    parameters = {"place": "Place name."}
    category = "geo"

    def call(self, place: str) -> APIResponse:
        return APIResponse(success=False, error="elevation service unavailable")


def make_registry():
    registry = APIRegistry()
    for api in (FakeGeocode(), FakeWeather(), BrokenElevation()):
        registry.register(api)
    return registry


def make_client(responses, settings=None, llm=None):
    registry = make_registry()
    app = create_app(
        settings=settings or Settings(rate_per_minute=100, daily_cap=1000),
        registry=registry,
        llm_factory=lambda: llm or EchoLLM(list(responses)),
        model_name="scripted",
        serve_site=False,
    )
    return TestClient(app), registry


def read_events(text):
    events = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        if not lines:
            continue
        name = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((name, data))
    return events


# --- successful runs ----------------------------------------------------------


def test_run_returns_answer_steps_and_retrieved_tools():
    client, registry = make_client(
        [
            ModelTurn(text="I need the coordinates first.", tool_calls=[ToolCall("geocode", {"place": "Lisbon"})]),
            "Lisbon is at 38.72, -9.14.",
        ]
    )

    res = client.post("/api/run", json={"question": "Where is Lisbon?", "strategy": "react", "top_k": 3})

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/json; charset=utf-8"
    run = res.json()
    assert run["final_answer"] == "Lisbon is at 38.72, -9.14."
    assert run["model"] == "scripted"
    assert run["tools_called"] == ["geocode"]
    assert {t["name"] for t in run["retrieved_tools"]} == {"geocode", "weather_forecast", "elevation"}
    assert all({"score", "category", "description"} <= set(t) for t in run["retrieved_tools"])
    step = run["steps"][0]
    assert step == {
        "index": 1,
        "node": None,
        "thought": "I need the coordinates first.",
        "tool": "geocode",
        "arguments": {"place": "Lisbon"},
        "observation": {"name": "Lisbon", "latitude": 38.72, "longitude": -9.14},
        "status": "ok",
        "backtracked": False,
    }
    assert run["num_steps"] == 2 and run["num_tool_calls"] == 1
    assert isinstance(run["latency_ms"], int)
    assert run["tree"] is None
    assert registry.get("geocode").calls == ["Lisbon"]


def test_run_keeps_unicode_as_utf8():
    client, _ = make_client(
        [ToolCall("weather_forecast", {"latitude": 1, "longitude": 2}), "It is 21 °C."]
    )

    res = client.post("/api/run", json={"question": "Weather in Lisbon?", "strategy": "react", "top_k": 3})

    assert "21 °C".encode("utf-8") in res.content
    assert res.json()["steps"][0]["observation"] == {"temperature": "21 °C"}


def test_stream_sends_events_in_order():
    client, _ = make_client([ToolCall("geocode", {"place": "Lisbon"}), "Found it."])

    res = client.get("/api/run/stream", params={"question": "Where is Lisbon?", "strategy": "react", "top_k": 2})

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = read_events(res.text)
    assert [name for name, _ in events] == ["retrieved", "step", "answer", "done"]
    assert events[0][1]["model"] == "scripted"
    assert events[-1][1]["final_answer"] == "Found it."


# --- tool error and backtracking ----------------------------------------------


def test_dfsdt_tool_error_backtracks_to_another_branch():
    client, _ = make_client(
        [
            ToolCall("elevation", {"place": "Lisbon"}),  # node 1: fails
            ToolCall("geocode", {"place": "Lisbon"}),  # node 2: works
            "Lisbon is at 38.72, -9.14.",  # node 3: answer
        ]
    )

    res = client.post("/api/run", json={"question": "How high is Lisbon?", "strategy": "dfsdt", "top_k": 3})

    run = res.json()
    failed, ok = run["steps"]
    assert failed["tool"] == "elevation" and failed["status"] == "error" and failed["backtracked"] is True
    assert "unavailable" in failed["observation"]
    assert ok["tool"] == "geocode" and ok["status"] == "ok" and ok["backtracked"] is False
    assert run["final_answer"] == "Lisbon is at 38.72, -9.14."
    assert run["tools_called"] == ["geocode"]
    tree = run["tree"]
    status = {node["id"]: node["status"] for node in tree["nodes"]}
    assert status == {0: "root", 1: "error", 2: "ok", 3: "answer"}
    assert tree["chosen_path"] == [0, 2, 3]
    assert tree["explored"] == 3


def test_stream_reports_the_backtrack():
    client, _ = make_client(
        [ToolCall("elevation", {"place": "Lisbon"}), ToolCall("geocode", {"place": "Lisbon"}), "Done."]
    )

    res = client.get("/api/run/stream", params={"question": "How high is Lisbon?", "strategy": "dfsdt", "top_k": 3})

    events = read_events(res.text)
    names = [name for name, _ in events]
    assert names == ["retrieved", "node", "step", "backtrack", "node", "step", "node", "answer", "done"]
    backtrack = events[3][1]
    assert backtrack["node"] == 1 and backtrack["reason"] == "tool_error" and backtrack["steps"] == [1]


# --- validation and limits ----------------------------------------------------


def test_rejects_a_question_over_300_characters():
    client, registry = make_client(["unused"])

    res = client.post("/api/run", json={"question": "x" * 301, "strategy": "react", "top_k": 3})

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "question_too_long"
    assert "300" in res.json()["error"]["message"]
    stream = client.get("/api/run/stream", params={"question": "x" * 301})
    assert stream.status_code == 400 and stream.json()["error"]["code"] == "question_too_long"


def test_rejects_an_invalid_strategy():
    client, _ = make_client(["unused"])

    res = client.post("/api/run", json={"question": "Where is Lisbon?", "strategy": "bfs", "top_k": 3})

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_strategy"


@pytest.mark.parametrize("top_k", [0, 11, "many", 2.5])
def test_rejects_an_invalid_top_k(top_k):
    client, _ = make_client(["unused"])

    res = client.post("/api/run", json={"question": "Where is Lisbon?", "strategy": "react", "top_k": top_k})

    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_top_k"


def test_rate_limit_per_visitor():
    client, _ = make_client([], settings=Settings(rate_per_minute=2, daily_cap=100), llm=EchoLLM(default_response="Hi."))
    body = {"question": "Hello?", "strategy": "react", "top_k": 1}

    assert client.post("/api/run", json=body).status_code == 200
    assert client.post("/api/run", json=body).status_code == 200
    res = client.post("/api/run", json=body)

    assert res.status_code == 429
    assert res.json()["error"]["code"] == "rate_limited"


def test_daily_cap_returns_demo_limit_message():
    client, _ = make_client([], settings=Settings(rate_per_minute=100, daily_cap=1), llm=EchoLLM(default_response="Hi."))
    body = {"question": "Hello?", "strategy": "react", "top_k": 1}

    assert client.post("/api/run", json=body).status_code == 200
    res = client.get("/api/run/stream", params=body)

    assert res.status_code == 429
    assert res.json()["error"]["code"] == "demo_limit"
    assert "Demo limit reached" in res.json()["error"]["message"]


def test_rate_limiter_window_slides():
    now = [1000.0]
    limiter = RateLimiter(per_minute=1, daily_cap=10, clock=lambda: now[0])
    limiter.hit("a")
    with pytest.raises(DemoError):
        limiter.hit("a")
    limiter.hit("b")
    now[0] += 61
    limiter.hit("a")


def test_tool_calls_are_capped():
    calls = [ToolCall("geocode", {"place": f"P{i}"}) for i in range(5)]
    settings = Settings(rate_per_minute=100, daily_cap=100, limits=Limits(max_tool_calls=2))
    client, registry = make_client(calls + ["Done."], settings=settings)

    run = client.post("/api/run", json={"question": "Where?", "strategy": "react", "top_k": 3}).json()

    assert len(registry.get("geocode").calls) == 2
    assert [s["status"] for s in run["steps"]][:3] == ["ok", "ok", "error"]


# --- no internals reach the browser -------------------------------------------


class ExplodingLLM(EchoLLM):
    def chat(self, system, messages, tools):
        raise RuntimeError(r"boom at C:\secret\path\agent.py line 12, key=abc123")


def test_model_failure_is_a_friendly_message():
    client, _ = make_client([], llm=ExplodingLLM())

    res = client.post("/api/run", json={"question": "Where is Lisbon?", "strategy": "react", "top_k": 1})

    assert res.status_code == 500
    assert res.json() == {
        "error": {"code": "agent_error", "message": "Something went wrong while running the agent. Please try again."}
    }

    stream = client.get("/api/run/stream", params={"question": "Where is Lisbon?"})
    events = read_events(stream.text)
    assert events[-1] == ("error", res.json()["error"])
    assert "secret" not in stream.text and "Traceback" not in stream.text


def test_rate_limited_model_is_reported_as_such():
    class Limited(EchoLLM):
        def chat(self, system, messages, tools):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    client, _ = make_client([], llm=Limited())
    res = client.post("/api/run", json={"question": "Where is Lisbon?", "strategy": "react", "top_k": 1})

    assert res.status_code == 503 and res.json()["error"]["code"] == "model_rate_limited"


def test_scrub_removes_secrets_keys_and_paths(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-very-secret-value")
    text = scrub(r"failed: sk-very-secret-value at C:\Users\me\app.py url=https://x.io/a?api_key=XYZ&q=1 /home/me/x")

    assert "sk-very-secret-value" not in text and "XYZ" not in text
    assert "Users" not in text and "/home/me" not in text
    assert "https://x.io/a?api_key=***&q=1" in text
    assert scrub("https://api.github.com/users/torvalds") == "https://api.github.com/users/torvalds"


# --- other endpoints ----------------------------------------------------------


def test_health_and_tools():
    client, _ = make_client([])

    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["model"] == "scripted"
    assert health["limits"]["max_question_chars"] == 300

    tools = client.get("/api/tools").json()["tools"]
    assert {t["name"] for t in tools} == {"geocode", "weather_forecast", "elevation"}
    geocode = next(t for t in tools if t["name"] == "geocode")
    assert geocode["category"] == "geo" and geocode["parameters"]["place"]["type"] == "string"


def test_unknown_api_path_is_json_404():
    client, _ = make_client([])

    res = client.get("/api/nothing")

    assert res.status_code == 404 and res.json()["error"]["code"] == "not_found"


def test_cors_allows_local_and_site_origins_only():
    client, _ = make_client([])

    local = client.get("/api/health", headers={"Origin": "http://localhost:5500"})
    site = client.get("/api/health", headers={"Origin": "https://mathurayush.github.io"})
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert local.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert site.headers["access-control-allow-origin"] == "https://mathurayush.github.io"
    assert "access-control-allow-origin" not in other.headers


def test_published_site_may_reach_a_local_server():
    client, _ = make_client([])
    preflight = {
        "Origin": "https://mathurayush.github.io",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Private-Network": "true",
    }

    res = client.options("/api/health", headers=preflight)
    other = client.options("/api/health", headers={**preflight, "Origin": "https://evil.example"})

    assert res.status_code == 200
    assert res.headers["access-control-allow-private-network"] == "true"
    assert res.headers["access-control-allow-origin"] == "https://mathurayush.github.io"
    assert "access-control-allow-origin" not in other.headers


def test_default_app_serves_the_site():
    from server.app import app

    client = TestClient(app)
    res = client.get("/index.html")

    assert res.status_code == 200 and "text/html" in res.headers["content-type"]
