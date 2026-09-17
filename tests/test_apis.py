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
