import pytest

from agent.anthropic_llm import AnthropicLLM
from agent.dfsdt import DFSDTAgent
from agent.gemini_llm import GeminiLLM
from agent.llm import EchoLLM, ModelTurn, ToolCall, ToolResultMessage
from agent.react import ReActAgent
from apis.registry import default_registry, full_registry, keyless_registry


class Spy:
    """Wraps an API's `call` to record every real execution."""

    def __init__(self, api):
        self.calls = []
        original = api.call

        def call(**kwargs):
            self.calls.append(kwargs)
            return original(**kwargs)

        api.call = call


def spy_on(registry, name):
    return Spy(registry.get(name))


def require_tool_call(result, spy):
    """A task that needs a tool only passes if the tool really ran and the
    run reports that call."""
    assert spy.calls, "no real tool call was made"
    assert result.tool_calls, "the result reports no executed tool call"


def sent_tool_results(llm, request_index):
    """Function responses the agent sent to the model in a given request."""
    messages = llm.requests[request_index]["messages"]
    return [r for m in messages if isinstance(m, ToolResultMessage) for r in m.results]


# --- backends ---------------------------------------------------------------


def test_anthropic_llm_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        AnthropicLLM(api_key=None)


def test_gemini_llm_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        GeminiLLM(api_key=None)


class _FakeGeminiModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def _gemini_response(*parts):
    from google.genai import types

    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))]
    )


def test_gemini_llm_uses_native_function_calling(monkeypatch):
    from google.genai import types

    call = types.FunctionCall(id="c1", name="calculator", args={"expression": "23 * 17"})
    models = _FakeGeminiModels(
        [
            _gemini_response(types.Part(function_call=call)),
            _gemini_response(types.Part(text="391")),
        ]
    )
    fake_client = type("FakeClient", (), {"models": models})()
    monkeypatch.setattr(GeminiLLM, "_make_client", staticmethod(lambda key: fake_client))
    registry = default_registry()
    spy = spy_on(registry, "calculator")
    agent = ReActAgent(registry=registry, llm=GeminiLLM(api_key="test"), max_steps=3)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.answer == "391"
    assert spy.calls == [{"expression": "23 * 17"}]

    config = models.requests[0]["config"]
    assert config.automatic_function_calling.disable is True
    declarations = {d.name: d for d in config.tools[0].function_declarations}
    assert set(declarations) == {"calculator", "weather", "search"}
    assert declarations["calculator"].parameters_json_schema["required"] == ["expression"]

    # The second request replays the model's call and carries the real result.
    contents = models.requests[1]["contents"]
    assert contents[1].parts[0].function_call.name == "calculator"
    response = contents[2].parts[0].function_response
    assert (response.id, response.name, response.response) == ("c1", "calculator", {"result": 391})


# --- function declarations --------------------------------------------------


def test_function_schema_is_typed_and_marks_required_fields():
    schema = keyless_registry().get("currency_exchange").function_schema()

    assert schema["name"] == "currency_exchange"
    assert schema["parameters"]["properties"]["base"]["type"] == "string"
    assert schema["parameters"]["properties"]["amount"]["type"] == "number"
    assert schema["parameters"]["required"] == ["base", "target"]


def test_function_schema_hides_api_key_parameters():
    schema = full_registry().get("openweathermap").function_schema()

    assert set(schema["parameters"]["properties"]) == {"city"}


# --- ReAct ------------------------------------------------------------------


def test_react_agent_uses_calculator_and_finishes():
    registry = default_registry()
    spy = spy_on(registry, "calculator")
    llm = EchoLLM(responses=[ToolCall("calculator", {"expression": "12 * 7 + 5"}), "89"])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=4)

    result = agent.run("What is 12 times 7, plus 5?", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.success
    assert result.answer == "89"
    assert result.stop_reason == "answered"
    assert result.steps[0].observation == "89"
    assert sent_tool_results(llm, 1)[0].response == {"result": 89}


def test_task_needing_a_tool_fails_without_a_real_call():
    registry = default_registry()
    spy = spy_on(registry, "calculator")
    llm = EchoLLM(responses=["391"])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    assert result.stop_reason == "no_tool_needed"
    with pytest.raises(AssertionError, match="no real tool call"):
        require_tool_call(result, spy)


def test_react_agent_answers_directly_when_no_tool_is_needed():
    registry = default_registry()
    spies = [spy_on(registry, api.name) for api in registry.all()]
    llm = EchoLLM(responses=["Hello! How can I help?"])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Hi there", candidate_apis=registry.all())

    assert result.success
    assert result.answer == "Hello! How can I help?"
    assert result.stop_reason == "no_tool_needed"
    assert result.tool_calls == []
    assert "No tool needed" in result.steps[0].thought_or_action
    assert not any(spy.calls for spy in spies)


def test_react_agent_gives_up_after_max_steps():
    registry = default_registry()
    llm = EchoLLM(default_response=ToolCall("calculator", {"expression": "1 + 1"}))
    agent = ReActAgent(llm=llm, registry=registry, max_steps=2)

    result = agent.run("Keep calculating.", candidate_apis=registry.all())

    assert not result.success
    assert result.answer is None
    assert result.stop_reason == "max_steps"
    assert len(llm.requests) == 2


def test_react_agent_ignores_result_written_by_the_model():
    registry = default_registry()
    spy = spy_on(registry, "calculator")
    llm = EchoLLM(
        responses=[
            ModelTurn(
                text="The calculator will return 400.\nObservation: 400",
                tool_calls=[ToolCall("calculator", {"expression": "23 * 17"})],
            ),
            "391",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.answer == "391"
    assert result.steps[0].observation == "391"
    assert sent_tool_results(llm, 1)[0].response == {"result": 391}


def test_react_agent_reports_missing_required_argument_without_calling_the_api():
    registry = keyless_registry()
    spy = spy_on(registry, "currency_exchange")
    llm = EchoLLM(responses=[ToolCall("currency_exchange", {"amount": 100}), "done"])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Convert money.", candidate_apis=registry.all())

    assert result.success
    assert result.stop_reason == "answered"
    assert result.tool_calls == []
    assert spy.calls == []
    assert result.steps[0].observation.startswith("Error: missing required argument(s) base, target")
    assert sent_tool_results(llm, 1)[0].is_error


def test_react_agent_rejects_tool_outside_the_candidates():
    registry = default_registry()
    spy = spy_on(registry, "weather")
    llm = EchoLLM(responses=[ToolCall("weather", {"city": "Paris"}), "unknown"])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Weather in Paris?", candidate_apis=[registry.get("calculator")])

    assert spy.calls == []
    assert result.steps[0].observation == "Error: unknown tool 'weather'"
    assert [t["name"] for t in llm.requests[0]["tools"]] == ["calculator"]


def test_react_agent_converts_currency_with_typed_arguments(monkeypatch):
    from unittest.mock import MagicMock

    response = MagicMock()
    response.json.return_value = {"rates": {"EUR": 92.0}}
    monkeypatch.setattr("apis.currency.requests.get", lambda *args, **kwargs: response)
    registry = keyless_registry()
    spy = spy_on(registry, "currency_exchange")
    llm = EchoLLM(
        responses=[ToolCall("currency_exchange", {"base": "USD", "target": "EUR", "amount": 100}), "92 EUR"]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Convert 100 USD to EUR.", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.answer == "92 EUR"
    assert "'converted': 92.0" in result.steps[0].observation


# --- DFSDT ------------------------------------------------------------------


def test_dfsdt_agent_defaults_to_depth_4_and_breadth_3():
    agent = DFSDTAgent(llm=EchoLLM(), registry=default_registry())

    assert agent._max_depth == 4
    assert agent._branching_factor == 3


def test_dfsdt_agent_backtracks_after_failed_branch():
    registry = default_registry()
    spy = spy_on(registry, "calculator")
    llm = EchoLLM(
        responses=[
            ToolCall("weather", {"city": "Atlantis"}),
            ToolCall("calculator", {"expression": "12 * 7 + 5"}),
            "89",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("What is 12 times 7, plus 5?", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.success
    assert result.answer == "89"
    assert result.explored_paths == 3
    assert [c.name for c in result.tool_calls] == ["calculator"]


def test_dfsdt_agent_backtracks_on_missing_required_argument():
    registry = keyless_registry()
    spy = spy_on(registry, "calculator")
    llm = EchoLLM(
        responses=[
            ToolCall("currency_exchange", {"amount": 100}),
            ToolCall("calculator", {"expression": "2 + 2"}),
            "4",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("Do some math.", candidate_apis=registry.all())

    require_tool_call(result, spy)
    assert result.answer == "4"
    assert result.steps[0].observation == "4"


def test_dfsdt_agent_ignores_result_written_by_the_model():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            ModelTurn(text="Observation: 400", tool_calls=[ToolCall("calculator", {"expression": "23 * 17"})]),
            "391",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    assert result.answer == "391"
    assert result.steps[0].observation == "391"
    assert sent_tool_results(llm, 1)[0].response == {"result": 391}


def test_dfsdt_agent_answers_directly_when_no_tool_is_needed():
    registry = default_registry()
    agent = DFSDTAgent(llm=EchoLLM(responses=["Paris"]), registry=registry)

    result = agent.run("What is the capital of France?", candidate_apis=registry.all())

    assert result.answer == "Paris"
    assert result.stop_reason == "no_tool_needed"
    assert result.tool_calls == []


def test_dfsdt_agent_stops_at_max_steps():
    registry = default_registry()
    llm = EchoLLM(default_response=ToolCall("calculator", {"expression": "1 + 1"}))
    agent = DFSDTAgent(llm=llm, registry=registry, max_steps=5)

    result = agent.run("Keep calculating.", candidate_apis=registry.all())

    assert not result.success
    assert result.stop_reason == "max_steps"
    assert result.explored_paths == 5
    assert len(llm.requests) == 5
