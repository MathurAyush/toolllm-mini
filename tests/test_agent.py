import pytest

from agent.anthropic_llm import AnthropicLLM
from agent.dfsdt import DFSDTAgent
from agent.llm import EchoLLM
from agent.react import ReActAgent
from apis.registry import default_registry


def test_anthropic_llm_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        AnthropicLLM(api_key=None)


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
