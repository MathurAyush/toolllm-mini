from apis.calculator import CalculatorAPI
from apis.registry import default_registry
from apis.search import SearchAPI
from apis.weather import WeatherAPI


def test_calculator_basic_expression():
    result = CalculatorAPI().call(expression="12 * 7 + 5")
    assert result.success
    assert result.data == 89


def test_calculator_rejects_unsupported_syntax():
    result = CalculatorAPI().call(expression="__import__('os')")
    assert not result.success


def test_calculator_refuses_huge_powers():
    for expression in ("9 ** 9 ** 9", "(10 ** 500) ** 3"):
        result = CalculatorAPI().call(expression=expression)
        assert not result.success and result.error == "Result too large."
    assert CalculatorAPI().call(expression="2 ** 64").data == 2**64
    assert CalculatorAPI().call(expression="2 ** -2").data == 0.25


def test_calculator_refuses_non_finite_results():
    result = CalculatorAPI().call(expression="1e308 * 10")
    assert not result.success


def test_weather_known_city():
    result = WeatherAPI().call(city="Tokyo")
    assert result.success
    assert result.data["condition"] == "Clear"


def test_weather_unknown_city():
    result = WeatherAPI().call(city="Atlantis")
    assert not result.success


def test_search_finds_matching_document():
    result = SearchAPI().call(query="Eiffel Tower Paris")
    assert result.success
    assert any("Eiffel Tower" in doc for doc in result.data)


def test_default_registry_contains_expected_apis():
    registry = default_registry()
    names = {api.name for api in registry.all()}
    assert names == {"calculator", "weather", "search"}
