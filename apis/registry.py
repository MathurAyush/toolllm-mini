from __future__ import annotations

from .animals import CatFactAPI, DogFactAPI, DogImageAPI
from .base import BaseAPI
from .books import AuthorSearchAPI, BookByISBNAPI, BookSearchAPI
from .calculator import CalculatorAPI
from .country import CountryInfoAPI
from .currency import CurrencyExchangeAPI
from .dates import LongWeekendsAPI, PublicHolidaysAPI, SunriseSunsetAPI, WorldTimeAPI
from .dictionary import DictionaryAPI
from .finance import CryptoPriceAPI, HistoricalExchangeRateAPI
from .food import CocktailSearchAPI, RandomRecipeAPI, RecipeSearchAPI
from .fun import AdviceAPI, ColorInfoAPI, HackerNewsSearchAPI, PokemonAPI, RelatedWordsAPI, TriviaQuestionsAPI
from .geo import (
    AirQualityAPI,
    ElevationAPI,
    GeocodeAPI,
    IPGeolocationAPI,
    RecentEarthquakesAPI,
    WeatherForecastAPI,
    ZipCodeAPI,
)
from .http import PublicAPI
from .joke import JokeAPI
from .news import NewsAPI
from .openweather import OpenWeatherMapAPI
from .people import AgeFromNameAPI, GitHubUserAPI, NationalityFromNameAPI, RandomUserAPI, UniversitySearchAPI
from .quotes import QuoteAPI
from .search import SearchAPI
from .space import ISSLocationAPI, NasaAPODAPI, NearEarthAsteroidsAPI, SpaceflightNewsAPI
from .units import UnitConversionAPI
from .weather import WeatherAPI
from .wikipedia import WikipediaSummaryAPI

# Wrappers around free public APIs that need no key of their own (NASA falls
# back to its shared DEMO_KEY and GitHub works unauthenticated); each one
# can run offline from a recorded mock response.
PUBLIC_APIS: tuple[type[PublicAPI], ...] = (
    GeocodeAPI,
    WeatherForecastAPI,
    AirQualityAPI,
    ElevationAPI,
    ZipCodeAPI,
    IPGeolocationAPI,
    RecentEarthquakesAPI,
    WorldTimeAPI,
    SunriseSunsetAPI,
    PublicHolidaysAPI,
    LongWeekendsAPI,
    HistoricalExchangeRateAPI,
    CryptoPriceAPI,
    BookSearchAPI,
    BookByISBNAPI,
    AuthorSearchAPI,
    RecipeSearchAPI,
    RandomRecipeAPI,
    CocktailSearchAPI,
    TriviaQuestionsAPI,
    NasaAPODAPI,
    NearEarthAsteroidsAPI,
    ISSLocationAPI,
    SpaceflightNewsAPI,
    CatFactAPI,
    DogFactAPI,
    DogImageAPI,
    RandomUserAPI,
    AgeFromNameAPI,
    NationalityFromNameAPI,
    UniversitySearchAPI,
    GitHubUserAPI,
    PokemonAPI,
    AdviceAPI,
    ColorInfoAPI,
    RelatedWordsAPI,
    HackerNewsSearchAPI,
    UnitConversionAPI,
)


class APIRegistry:
    def __init__(self) -> None:
        self._apis: dict[str, BaseAPI] = {}

    def register(self, api: BaseAPI) -> None:
        self._apis[api.name] = api

    def get(self, name: str) -> BaseAPI | None:
        return self._apis.get(name)

    def all(self) -> list[BaseAPI]:
        return list(self._apis.values())

    def catalog(self) -> list[dict]:
        """Structured registry entry for every registered API."""
        return [api.registry_entry() for api in self._apis.values()]


def _register_public_apis(registry: APIRegistry) -> None:
    for api_cls in PUBLIC_APIS:
        registry.register(api_cls())


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
    _register_public_apis(registry)
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
    _register_public_apis(registry)
    return registry
