from unittest.mock import MagicMock, patch

from apis.country import CountryInfoAPI
from apis.currency import CurrencyExchangeAPI
from apis.dictionary import DictionaryAPI
from apis.joke import JokeAPI
from apis.news import NewsAPI
from apis.openweather import OpenWeatherMapAPI
from apis.quotes import QuoteAPI
from apis.wikipedia import WikipediaSummaryAPI


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def test_openweathermap_requires_api_key():
    result = OpenWeatherMapAPI().call(city="London", api_key=None)
    assert not result.success
    assert "key" in result.error.lower()


@patch("apis.openweather.requests.get")
def test_openweathermap_success(mock_get):
    mock_get.return_value = _mock_response(
        {
            "name": "London",
            "weather": [{"description": "light rain"}],
            "main": {"temp": 14.2, "humidity": 82},
            "wind": {"speed": 4.6},
        }
    )
    result = OpenWeatherMapAPI().call(city="London", api_key="dummy-key")
    assert result.success
    assert result.data["condition"] == "light rain"
    assert result.data["temperature_c"] == 14.2


@patch("apis.currency.requests.get")
def test_currency_exchange_success(mock_get):
    mock_get.return_value = _mock_response({"rates": {"EUR": 0.9231}})
    result = CurrencyExchangeAPI().call(base="USD", target="EUR")
    assert result.success
    assert result.data["converted"] == 0.9231


@patch("apis.wikipedia.requests.get")
def test_wikipedia_summary_success(mock_get):
    mock_get.return_value = _mock_response(
        {
            "title": "Python (programming language)",
            "extract": "Python is a high-level, general-purpose programming language.",
            "content_urls": {
                "desktop": {"page": "https://en.wikipedia.org/wiki/Python_(programming_language)"}
            },
        }
    )
    result = WikipediaSummaryAPI().call(title="Python (programming language)")
    assert result.success
    assert "Python" in result.data["extract"]


def test_news_requires_api_key():
    result = NewsAPI().call(query="technology", api_key=None)
    assert not result.success


@patch("apis.news.requests.get")
def test_news_success(mock_get):
    mock_get.return_value = _mock_response(
        {
            "totalResults": 1,
            "articles": [
                {"title": "Example Headline", "source": {"name": "Example News"}, "url": "https://example.com"}
            ],
        }
    )
    result = NewsAPI().call(query="technology", api_key="dummy-key")
    assert result.success
    assert result.data["articles"][0]["title"] == "Example Headline"


@patch("apis.joke.requests.get")
def test_joke_success(mock_get):
    mock_get.return_value = _mock_response(
        {
            "category": "Programming",
            "joke": "Why do programmers prefer dark mode? Because light attracts bugs.",
        }
    )
    result = JokeAPI().call(category="Programming")
    assert result.success
    assert "bugs" in result.data["joke"]


@patch("apis.quotes.requests.get")
def test_quote_success(mock_get):
    mock_get.return_value = _mock_response(
        {
            "content": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs",
        }
    )
    result = QuoteAPI().call()
    assert result.success
    assert result.data["author"] == "Steve Jobs"


@patch("apis.dictionary.requests.get")
def test_dictionary_success(mock_get):
    mock_get.return_value = _mock_response(
        [
            {
                "word": "serendipity",
                "phonetic": "/ser.en.DIP.i.tee/",
                "meanings": [
                    {
                        "partOfSpeech": "noun",
                        "definitions": [
                            {"definition": "The occurrence of events by chance in a happy way."}
                        ],
                    }
                ],
            }
        ]
    )
    result = DictionaryAPI().call(word="serendipity")
    assert result.success
    assert result.data["meanings"][0]["part_of_speech"] == "noun"


@patch("apis.country.requests.get")
def test_country_info_success(mock_get):
    mock_get.return_value = _mock_response(
        [
            {
                "name": {"common": "Japan"},
                "capital": ["Tokyo"],
                "region": "Asia",
                "population": 125836021,
                "currencies": {"JPY": {"name": "Japanese yen"}},
            }
        ]
    )
    result = CountryInfoAPI().call(name="Japan")
    assert result.success
    assert result.data["capital"] == "Tokyo"
    assert result.data["currencies"] == ["JPY"]
