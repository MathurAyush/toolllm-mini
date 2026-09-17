from __future__ import annotations

from .base import BaseAPI
from .calculator import CalculatorAPI
from .country import CountryInfoAPI
from .currency import CurrencyExchangeAPI
from .dictionary import DictionaryAPI
from .joke import JokeAPI
from .news import NewsAPI
from .openweather import OpenWeatherMapAPI
from .quotes import QuoteAPI
from .search import SearchAPI
from .weather import WeatherAPI
from .wikipedia import WikipediaSummaryAPI


class APIRegistry:
    def __init__(self) -> None:
        self._apis: dict[str, BaseAPI] = {}

    def register(self, api: BaseAPI) -> None:
        self._apis[api.name] = api

    def get(self, name: str) -> BaseAPI | None:
        return self._apis.get(name)

    def all(self) -> list[BaseAPI]:
        return list(self._apis.values())


def default_registry() -> APIRegistry:
    registry = APIRegistry()
    registry.register(CalculatorAPI())
    registry.register(WeatherAPI())
    registry.register(SearchAPI())
    return registry


def full_registry() -> APIRegistry:
    """Registry including the mock offline APIs plus all real-world API
    wrappers, for a richer catalog to search over in retrieval demos."""
    registry = default_registry()
    registry.register(OpenWeatherMapAPI())
    registry.register(CurrencyExchangeAPI())
    registry.register(WikipediaSummaryAPI())
    registry.register(NewsAPI())
    registry.register(JokeAPI())
    registry.register(QuoteAPI())
    registry.register(DictionaryAPI())
    registry.register(CountryInfoAPI())
    return registry


def keyless_registry() -> APIRegistry:
    """Registry of every API that needs no API key of its own (excludes
    OpenWeatherMap and NewsAPI), so an agent benchmark only needs an LLM
    credential to run end to end."""
    registry = default_registry()
    registry.register(CurrencyExchangeAPI())
    registry.register(WikipediaSummaryAPI())
    registry.register(JokeAPI())
    registry.register(QuoteAPI())
    registry.register(DictionaryAPI())
    registry.register(CountryInfoAPI())
    return registry
