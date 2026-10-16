import pytest

from agent.anthropic_llm import AnthropicLLM
from agent.dfsdt import DFSDTAgent
from agent.gemini_llm import GeminiLLM
from agent.llm import EchoLLM
from agent.react import ReActAgent
from apis.registry import default_registry, keyless_registry


def test_anthropic_llm_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        AnthropicLLM(api_key=None)


def test_gemini_llm_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        GeminiLLM(api_key=None)


def test_react_agent_uses_calculator_and_finishes():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            "Thought: I should compute this.\nAction: calculator[12 * 7 + 5]",
            "Thought: I have the result.\nFinish[89]",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=4)

    result = agent.run("What is 12 times 7, plus 5?", candidate_apis=registry.all())

    assert result.success
    assert result.answer == "89"
    assert result.steps[0].observation == "89"


def test_react_agent_gives_up_after_max_steps():
    registry = default_registry()
    llm = EchoLLM(responses=["Thought: still thinking."])
    agent = ReActAgent(llm=llm, registry=registry, max_steps=2)

    result = agent.run("Unanswerable question.", candidate_apis=registry.all())

    assert not result.success
    assert result.answer is None


def test_dfsdt_agent_backtracks_after_failed_branch():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            "Action: weather[city=Atlantis]",
            "Action: calculator[12 * 7 + 5]",
            "Finish[89]",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("What is 12 times 7, plus 5?", candidate_apis=registry.all())

    assert result.success
    assert result.answer == "89"
    assert result.explored_paths == 3


def test_dfsdt_agent_defaults_to_depth_4_and_breadth_3():
    registry = default_registry()
    llm = EchoLLM(responses=["Thought: still thinking."])
    agent = DFSDTAgent(llm=llm, registry=registry)

    assert agent._max_depth == 4
    assert agent._branching_factor == 3


def test_react_agent_survives_api_call_missing_required_argument():
    registry = keyless_registry()
    llm = EchoLLM(
        responses=[
            "Action: currency_exchange[100]",
            "Finish[done]",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Convert money.", candidate_apis=registry.all())

    assert result.success
    assert result.answer == "done"
    assert result.steps[0].observation.startswith("Error:")


def test_react_agent_ignores_made_up_observation_and_runs_the_tool():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            "Thought: compute.\nAction: calculator[23 * 17]\nObservation: 400\nFinish[400]",
            "Thought: the tool says 391.\nFinish[391]",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    assert result.answer == "391"
    assert len(result.steps) == 2
    assert result.steps[0].observation == "391"
    assert "400" not in result.steps[0].thought_or_action


def test_react_agent_runs_action_written_before_a_guessed_finish():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            "Action: weather[Tokyo]\nFinish[It is rainy in Tokyo.]",
            "Finish[Clear, 27 C]",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Weather in Tokyo?", candidate_apis=registry.all())

    assert result.answer == "Clear, 27 C"
    assert "Clear" in result.steps[0].observation


def test_dfsdt_agent_ignores_made_up_observation_and_runs_the_tool():
    registry = default_registry()
    llm = EchoLLM(
        responses=[
            "Action: calculator[23 * 17]\nObservation: 400\nFinish[400]",
            "Finish[391]",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("What is 23 times 17?", candidate_apis=registry.all())

    assert result.answer == "391"
    assert result.steps[0].observation == "391"


def test_react_agent_converts_currency_with_keyword_arguments(monkeypatch):
    from unittest.mock import MagicMock

    response = MagicMock()
    response.json.return_value = {"rates": {"EUR": 92.0}}
    monkeypatch.setattr("apis.currency.requests.get", lambda *args, **kwargs: response)
    registry = keyless_registry()
    llm = EchoLLM(
        responses=[
            "Action: currency_exchange[base=USD, target=EUR, amount=100]",
            "Finish[92 EUR]",
        ]
    )
    agent = ReActAgent(llm=llm, registry=registry, max_steps=3)

    result = agent.run("Convert 100 USD to EUR.", candidate_apis=registry.all())

    assert result.answer == "92 EUR"
    assert "'converted': 92.0" in result.steps[0].observation


def test_dfsdt_agent_backtracks_on_api_call_missing_required_argument():
    registry = keyless_registry()
    llm = EchoLLM(
        responses=[
            "Action: currency_exchange[100]",
            "Action: calculator[2 + 2]",
            "Finish[4]",
        ]
    )
    agent = DFSDTAgent(llm=llm, registry=registry, max_depth=3, branching_factor=2)

    result = agent.run("Do some math.", candidate_apis=registry.all())

    assert result.success
    assert result.answer == "4"
