"""Tests for the public API wrappers in apis/. Every tool test runs offline
from the tool's recorded mock payload; the conftest also sets
TOOLLLM_OFFLINE=1 so nothing here touches the network."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from apis.animals import CatFactAPI, DogFactAPI, DogImageAPI
from apis.books import AuthorSearchAPI, BookByISBNAPI, BookSearchAPI
from apis.dates import LongWeekendsAPI, PublicHolidaysAPI, SunriseSunsetAPI, WorldTimeAPI
from apis.finance import CryptoPriceAPI, HistoricalExchangeRateAPI
from apis.food import CocktailSearchAPI, RandomRecipeAPI, RecipeSearchAPI
from apis.fun import AdviceAPI, ColorInfoAPI, HackerNewsSearchAPI, PokemonAPI, RelatedWordsAPI, TriviaQuestionsAPI
from apis.geo import (
    AirQualityAPI,
    ElevationAPI,
    GeocodeAPI,
    IPGeolocationAPI,
    RecentEarthquakesAPI,
    WeatherForecastAPI,
    ZipCodeAPI,
)
from apis.http import OFFLINE_ENV, Param, PublicAPI
from apis.people import AgeFromNameAPI, GitHubUserAPI, NationalityFromNameAPI, RandomUserAPI, UniversitySearchAPI
from apis.registry import PUBLIC_APIS, full_registry, keyless_registry
from apis.space import ISSLocationAPI, NasaAPODAPI, NearEarthAsteroidsAPI, SpaceflightNewsAPI
from apis.units import UnitConversionAPI
from retriever.retriever import APIRetriever

PUBLIC_IDS = [cls.name for cls in PUBLIC_APIS]


def offline(api_cls):
    return api_cls(offline=True)


def _response(payload=None, status=200, json_error=False):
    mock = MagicMock()
    mock.status_code = status
    if json_error:
        mock.json.side_effect = ValueError("not json")
    else:
        mock.json.return_value = payload
    return mock


# --- One test per tool, run from its mock payload ------------------------


def test_geocode():
    result = offline(GeocodeAPI).call(place="Berlin")
    assert result.success
    assert result.data["country"] == "Germany"
    assert result.data["latitude"] == pytest.approx(52.52, abs=0.01)


def test_weather_forecast():
    result = offline(WeatherForecastAPI).call(latitude=52.52, longitude=13.41, days=1)
    assert result.success
    assert result.data["days"] == [{"date": "2026-10-23", "temp_max_c": 14.0, "temp_min_c": 6.2, "precipitation_mm": 0.0}]


def test_air_quality():
    result = offline(AirQualityAPI).call(latitude=52.52, longitude=13.41)
    assert result.success
    assert result.data["us_aqi"] == 38


def test_elevation():
    result = offline(ElevationAPI).call(latitude="27.98", longitude="86.92")
    assert result.success
    assert result.data == {"latitude": 27.98, "longitude": 86.92, "elevation_m": 7533.0}


def test_zip_code_lookup():
    result = offline(ZipCodeAPI).call(postal_code="90210")
    assert result.success
    assert result.data["places"][0]["name"] == "Beverly Hills"
    assert result.data["places"][0]["latitude"] == 34.0901


def test_ip_geolocation():
    result = offline(IPGeolocationAPI).call(ip="8.8.8.8")
    assert result.success
    assert result.data["isp"] == "Google LLC"
    assert result.data["timezone"] == "America/Los_Angeles"


def test_recent_earthquakes():
    result = offline(RecentEarthquakesAPI).call(min_magnitude=5, limit=1)
    assert result.success
    assert result.data[0]["magnitude"] == 5
    assert result.data[0]["time_utc"] == "2026-10-21T19:25:04Z"
    assert result.data[0]["tsunami"] is False


def test_world_time():
    result = offline(WorldTimeAPI).call(timezone="Asia/Tokyo")
    assert result.success
    assert result.data["date"] == "2026-10-23"
    assert result.data["day_of_week"] == "Friday"


def test_sunrise_sunset():
    result = offline(SunriseSunsetAPI).call(latitude=48.85, longitude=2.35, date="2025-06-21")
    assert result.success
    assert result.data["sunrise_utc"] == "2025-06-21T03:47:01+00:00"
    assert result.data["day_length_hours"] == 16.18


def test_public_holidays():
    result = offline(PublicHolidaysAPI).call(country_code="de", year="2025")
    assert result.success
    assert result.data["country_code"] == "DE"
    assert result.data["year"] == 2025
    assert result.data["holidays"][0]["name"] == "New Year's Day"


def test_long_weekends():
    result = offline(LongWeekendsAPI).call(country_code="DE", year=2025)
    assert result.success
    assert result.data[1]["bridge_days"] == ["2025-05-02"]


def test_historical_exchange_rate():
    result = offline(HistoricalExchangeRateAPI).call(base="usd", target="eur", date="2020-01-02")
    assert result.success
    assert result.data["rate"] == 0.89342


def test_crypto_price():
    result = offline(CryptoPriceAPI).call(coin="Bitcoin")
    assert result.success
    assert result.data["price"] == 81670
    assert result.data["change_24h_pct"] == -1.28


def test_book_search():
    result = offline(BookSearchAPI).call(query="dune")
    assert result.success
    assert result.data["books"][0]["authors"] == ["Frank Herbert"]
    assert result.data["books"][0]["first_publish_year"] == 1965


def test_book_by_isbn():
    result = offline(BookByISBNAPI).call(isbn="978-0441172719")
    assert result.success
    assert result.data["isbn"] == "9780441172719"
    assert result.data["pages"] == 896


def test_author_search():
    result = offline(AuthorSearchAPI).call(name="Tolkien")
    assert result.success
    assert result.data["top_work"] == "The Hobbit"


def test_recipe_search():
    result = offline(RecipeSearchAPI).call(dish="arrabiata")
    assert result.success
    assert result.data[0]["cuisine"] == "Italian"
    # Empty and missing ingredient slots are dropped.
    assert result.data[0]["ingredients"] == ["1 pound penne rigate", "1/4 cup olive oil", "3 cloves garlic"]


def test_random_recipe():
    result = offline(RandomRecipeAPI).call()
    assert result.success
    assert result.data["name"] == "Spicy Arrabiata Penne"


def test_cocktail_search():
    result = offline(CocktailSearchAPI).call(drink="margarita")
    assert result.success
    assert result.data[0]["alcoholic"] is True
    assert "Salt" in result.data[0]["ingredients"]


def test_trivia_questions():
    result = offline(TriviaQuestionsAPI).call(amount=1, topic="Science", difficulty="EASY")
    assert result.success
    question = result.data[0]
    assert question["category"] == "Science & Nature"  # HTML entities decoded
    assert question["correct_answer"] in question["options"]


def test_nasa_apod():
    result = offline(NasaAPODAPI).call(date="2024-01-15")
    assert result.success
    assert result.data["title"] == "The Medusa Nebula"
    assert result.data["copyright"] == "Example Observatory"


def test_near_earth_asteroids():
    result = offline(NearEarthAsteroidsAPI).call(date="2024-01-01")
    assert result.success
    assert result.data["count"] == 1
    assert result.data["asteroids"][0]["hazardous"] is False
    assert result.data["asteroids"][0]["miss_distance_km"] == 65417380


def test_iss_location():
    result = offline(ISSLocationAPI).call()
    assert result.success
    assert result.data["altitude_km"] == 418.3


def test_spaceflight_news():
    result = offline(SpaceflightNewsAPI).call(topic="mars", limit=1)
    assert result.success
    assert "Mars" in result.data["articles"][0]["title"]


def test_cat_fact():
    result = offline(CatFactAPI).call()
    assert result.success
    assert "paws" in result.data["fact"]


def test_dog_fact():
    result = offline(DogFactAPI).call()
    assert result.success
    assert "Mastiff" in result.data["fact"]


def test_dog_image():
    result = offline(DogImageAPI).call(breed="husky")
    assert result.success
    assert result.data["image_url"].startswith("https://images.dog.ceo/")


def test_random_user():
    result = offline(RandomUserAPI).call(count=1, nationality="us")
    assert result.success
    assert result.data[0]["name"] == "Tara Holland"
    assert result.data[0]["age"] == 39


def test_age_from_name():
    result = offline(AgeFromNameAPI).call(name="Michael")
    assert result.success
    assert result.data["estimated_age"] == 57


def test_nationality_from_name():
    result = offline(NationalityFromNameAPI).call(name="Nathaniel")
    assert result.success
    assert len(result.data["countries"]) == 3
    assert result.data["countries"][0] == {"country_code": "US", "probability": 0.358}


def test_university_search():
    result = offline(UniversitySearchAPI).call(name="oxford", limit=1)
    assert result.success
    assert result.data["total"] == 2
    assert result.data["universities"] == [
        {
            "name": "Oxford Brookes University",
            "country": "United Kingdom",
            "website": "http://www.brookes.ac.uk/",
            "domains": ["brookes.ac.uk"],
        }
    ]


def test_github_user():
    result = offline(GitHubUserAPI).call(username="torvalds")
    assert result.success
    assert result.data["name"] == "Linus Torvalds"
    assert result.data["url"] == "https://github.com/torvalds"


def test_pokemon_info():
    result = offline(PokemonAPI).call(pokemon="Pikachu")
    assert result.success
    assert result.data["types"] == ["electric"]
    assert result.data["height_m"] == 0.4
    assert result.data["base_stats"]["speed"] == 90


def test_advice():
    result = offline(AdviceAPI).call()
    assert result.success
    assert "friends" in result.data["advice"]


def test_color_info():
    result = offline(ColorInfoAPI).call(hex="#0047AB")
    assert result.success
    assert result.data["name"] == "Cobalt"


def test_related_words():
    result = offline(RelatedWordsAPI).call(word="happy", relation="Synonyms", limit=2)
    assert result.success
    assert result.data == {"word": "happy", "relation": "synonyms", "words": ["glad", "felicitous"]}


def test_hacker_news_search():
    result = offline(HackerNewsSearchAPI).call(query="rust", limit=1)
    assert result.success
    assert result.data["stories"][0]["discussion"] == "https://news.ycombinator.com/item?id=22238335"


def test_unit_conversion():
    api = UnitConversionAPI()
    assert api.call(value=10, from_unit="miles", to_unit="km").data["result"] == 16.09344
    assert api.call(value="212", from_unit="F", to_unit="celsius").data["result"] == 100.0
    assert not api.call(value=1, from_unit="kg", to_unit="km").success


# --- Catalog and wrapper behavior shared by every public API ---------------


def test_catalog_has_at_least_forty_tools():
    assert len(full_registry().all()) >= 40
    assert len(PUBLIC_APIS) == len(set(PUBLIC_IDS))


@pytest.mark.parametrize("api", full_registry().all(), ids=lambda api: api.name)
def test_every_tool_has_a_complete_registry_entry(api):
    entry = api.registry_entry()
    assert entry["name"] and entry["description"] and entry["category"]
    assert set(entry["required"]) <= set(entry["parameters"])
    assert set(entry["example_call"]) <= set(entry["parameters"])
    assert set(entry["required"]) <= set(entry["example_call"])
    assert entry["example_response"] is not None
    for prop in entry["parameters"].values():
        assert prop["type"] in {"string", "integer", "number", "boolean"}
        assert prop["description"]


@pytest.mark.parametrize("api_cls", PUBLIC_APIS, ids=PUBLIC_IDS)
def test_example_call_returns_example_response(api_cls):
    result = api_cls(offline=True).call(**api_cls.example_call)
    assert result.success, result.error
    assert result.data == api_cls.example_response


@pytest.mark.parametrize("api_cls", PUBLIC_APIS, ids=PUBLIC_IDS)
def test_live_request_parses_like_the_mock(api_cls):
    """The live path sends one GET with a timeout and parses the reply the
    same way the offline path parses the mock."""
    with patch("apis.http.requests.get", return_value=_response(api_cls.mock_payload)) as get:
        result = api_cls(offline=False).call(**api_cls.example_call)
    assert result.success, result.error
    assert result.data == api_cls.example_response
    if api_cls is not UnitConversionAPI:
        assert get.call_count == 1
        assert get.call_args.args[0].startswith(("https://", "http://"))
        assert get.call_args.kwargs["timeout"] == api_cls.timeout


@pytest.mark.parametrize(
    "api_cls, args, prefix",
    [
        (PokemonAPI, {"pokemon": "../../users"}, "https://pokeapi.co/api/v2/pokemon/"),
        (GitHubUserAPI, {"username": "a/../../repos"}, "https://api.github.com/users/"),
    ],
)
def test_path_arguments_cannot_leave_the_endpoint(api_cls, args, prefix):
    """A model-chosen argument in the URL path is one escaped segment, so
    it cannot point the request at another path."""
    with patch("apis.http.requests.get", return_value=_response(api_cls.mock_payload)) as get:
        api_cls(offline=False).call(**args)
    url = get.call_args.args[0]
    assert url.startswith(prefix)
    assert "/" not in url[len(prefix):]


def test_offline_env_var_serves_the_mock(monkeypatch):
    monkeypatch.setenv(OFFLINE_ENV, "1")
    with patch("apis.http.requests.get") as get:
        assert GeocodeAPI().call(place="Berlin").success
    get.assert_not_called()


def test_timeout_is_reported_as_an_error():
    with patch("apis.http.requests.get", side_effect=requests.Timeout()):
        result = GeocodeAPI(offline=False).call(place="Berlin")
    assert not result.success
    assert "timed out" in result.error


def test_live_failure_does_not_fall_back_to_mock_data():
    with patch("apis.http.requests.get", side_effect=requests.ConnectionError("offline")):
        result = CatFactAPI(offline=False).call()
    assert not result.success
    assert result.data is None


@pytest.mark.parametrize(
    "status, message",
    [(404, "nothing found"), (429, "rate limit"), (500, "HTTP 500")],
)
def test_http_errors_are_reported(status, message):
    with patch("apis.http.requests.get", return_value=_response({}, status=status)):
        result = PokemonAPI(offline=False).call(pokemon="missingno")
    assert not result.success
    assert message in result.error


def test_non_json_response_is_reported():
    with patch("apis.http.requests.get", return_value=_response(json_error=True)):
        result = AdviceAPI(offline=False).call()
    assert not result.success
    assert "not JSON" in result.error


def test_unexpected_payload_shape_is_reported():
    with patch("apis.http.requests.get", return_value=_response({"unexpected": True})):
        result = ISSLocationAPI(offline=False).call()
    assert not result.success
    assert "Unexpected response" in result.error


def test_empty_result_is_reported():
    with patch("apis.http.requests.get", return_value=_response({"results": []})):
        result = GeocodeAPI(offline=False).call(place="Nowhereville")
    assert not result.success
    assert "Nowhereville" in result.error


def test_arguments_are_validated_and_coerced():
    api = WeatherForecastAPI(offline=True)
    assert "Missing required argument 'latitude'" in api.call(longitude=1).error
    assert "must be a number" in api.call(latitude="north", longitude=1).error
    assert "must be an integer" in api.call(latitude=1, longitude=1, days="2.5").error
    assert "Unknown argument" in api.call(latitude=1, longitude=1, city="Paris").error
    assert "must be one of" in RelatedWordsAPI(offline=True).call(word="cat", relation="hypernyms").error
    assert api.call(latitude="52.5", longitude="13.4", days="2").success


def test_boolean_parameters_accept_text():
    class Flag(PublicAPI):
        name = "flag"
        params = (Param("on", "boolean", "A flag."),)
        mock_payload = {}

        def parse(self, payload, on):
            return on

    assert Flag(offline=True).call(on="true").data is True
    assert Flag(offline=True).call(on="no").data is False
    assert not Flag(offline=True).call(on="maybe").success


def test_function_schema_marks_required_and_enum_parameters():
    schema = RelatedWordsAPI().function_schema()
    assert schema["parameters"]["required"] == ["word", "relation"]
    assert schema["parameters"]["properties"]["relation"]["enum"][0] == "rhymes"
    assert schema["parameters"]["properties"]["limit"]["type"] == "integer"


def test_keys_are_read_from_the_environment(monkeypatch):
    monkeypatch.delenv("NASA_API_KEY", raising=False)
    assert NasaAPODAPI().api_key() == "DEMO_KEY"
    monkeypatch.setenv("NASA_API_KEY", "nasa-test-key")
    with patch("apis.http.requests.get", return_value=_response(NasaAPODAPI.mock_payload)) as get:
        NasaAPODAPI(offline=False).call()
    assert get.call_args.kwargs["params"]["api_key"] == "nasa-test-key"
    assert "api_key" not in NasaAPODAPI().function_schema()["parameters"]["properties"]


def test_github_token_is_sent_when_set(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
    with patch("apis.http.requests.get", return_value=_response(GitHubUserAPI.mock_payload)) as get:
        GitHubUserAPI(offline=False).call(username="torvalds")
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer gh-test-token"


# --- Retrieval over the expanded catalog ---------------------------------

RETRIEVAL_QUERIES = {
    "geocode": "What are the latitude and longitude coordinates of Lisbon?",
    "weather_forecast": "What is the weather forecast for the next five days?",
    "air_quality": "How polluted is the air in Delhi today?",
    "elevation": "What is the elevation above sea level of Denver?",
    "zip_code_lookup": "Which town has the ZIP code 10001?",
    "ip_geolocation": "Where is the IP address 1.1.1.1 located?",
    "recent_earthquakes": "Have there been any big earthquakes recently?",
    "world_time": "What time is it right now in Tokyo?",
    "sunrise_sunset": "When is sunset in Paris tomorrow?",
    "public_holidays": "List the public holidays in Canada for 2026.",
    "long_weekends": "When are the long weekends in Germany next year?",
    "historical_exchange_rate": "What was the euro to dollar exchange rate on 2015-03-10?",
    "crypto_price": "How much is one bitcoin worth right now?",
    "book_search": "Search for books about dragons.",
    "book_by_isbn": "Which book has ISBN 9780140328721?",
    "author_search": "When was the author Jane Austen born?",
    "recipe_search": "Give me a recipe for chicken curry.",
    "random_recipe": "I don't know what to cook for dinner tonight, any ideas?",
    "cocktail_search": "How do I make a mojito cocktail?",
    "trivia_questions": "Give me three hard history trivia questions for a quiz.",
    "nasa_apod": "Show me NASA's astronomy picture of the day.",
    "near_earth_asteroids": "Are any asteroids passing close to Earth today?",
    "iss_location": "Where is the International Space Station right now?",
    "spaceflight_news": "What's the latest news about SpaceX rocket launches?",
    "cat_fact": "Tell me a fun fact about cats.",
    "dog_fact": "Tell me a fact about dogs.",
    "dog_image": "Show me a picture of a golden retriever dog.",
    "random_user": "Generate 5 fake user profiles for test data.",
    "age_from_name": "How old is someone named Olivia likely to be?",
    "nationality_from_name": "Which country does the name Giuseppe probably come from?",
    "university_search": "List universities in Canada with Toronto in the name.",
    "github_user": "How many followers does the GitHub user gvanrossum have?",
    "pokemon_info": "What type is the Pokemon Charizard?",
    "advice": "Can you give me some advice?",
    "color_info": "What is the name of the color with hex code #FF5733?",
    "related_words": "What words rhyme with orange?",
    "hacker_news_search": "Find Hacker News stories about Python.",
    "unit_conversion": "Convert 5 miles to kilometers.",
}


def test_every_public_api_has_a_retrieval_query():
    assert set(RETRIEVAL_QUERIES) == set(PUBLIC_IDS)


@pytest.fixture(scope="module")
def keyless_retriever():
    return APIRetriever(keyless_registry().all())


@pytest.mark.parametrize("expected, instruction", RETRIEVAL_QUERIES.items(), ids=list(RETRIEVAL_QUERIES))
def test_retriever_finds_each_public_api(keyless_retriever, expected, instruction):
    top = [hit.api.name for hit in keyless_retriever.retrieve(instruction, top_k=3)]
    assert expected in top
