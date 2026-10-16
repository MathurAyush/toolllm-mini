from agent.parsing import parse_action, parse_args, parse_step, truncate_at_observation
from apis.registry import full_registry

REGISTRY = full_registry()


def test_truncate_drops_made_up_observation_and_finish():
    response = "Thought: compute.\nAction: calculator[23 * 17]\nObservation: 400\nFinish[400]"

    assert truncate_at_observation(response) == "Thought: compute.\nAction: calculator[23 * 17]"


def test_truncate_leaves_reply_without_observation_unchanged():
    response = "Thought: done.\nFinish[391]"

    assert truncate_at_observation(response) == response


def test_parse_step_prefers_action_written_before_finish():
    action, finish = parse_step("Action: calculator[2 + 2]\nFinish[5]")

    assert finish is None
    assert action.groups() == ("calculator", "2 + 2")


def test_parse_step_returns_finish_when_it_comes_first():
    action, finish = parse_step("Thought: I know this.\nFinish[Tokyo]")

    assert action is None
    assert finish.group(1) == "Tokyo"


def test_action_arguments_stop_at_end_of_line():
    match = parse_action("Action: calculator[23 * 17]\nObservation: 391\nFinish[391]")

    assert match.group(2) == "23 * 17"


def test_keyword_value_with_comma_stays_whole():
    kwargs = parse_args("city=London,GB", REGISTRY.get("openweathermap"))

    assert kwargs == {"city": "London,GB"}


def test_keyword_arguments_split_only_before_new_keys():
    kwargs = parse_args("base=USD, target='EUR', amount=100", REGISTRY.get("currency_exchange"))

    assert kwargs == {"base": "USD", "target": "EUR", "amount": "100"}


def test_positional_arguments_map_onto_parameters_in_order():
    kwargs = parse_args("USD, EUR, 100", REGISTRY.get("currency_exchange"))

    assert kwargs == {"base": "USD", "target": "EUR", "amount": "100"}


def test_single_argument_tool_keeps_commas_in_value():
    assert parse_args("2,000 + 5", REGISTRY.get("calculator")) == {"expression": "2,000 + 5"}
    assert parse_args("London,GB", REGISTRY.get("openweathermap")) == {"city": "London,GB"}
