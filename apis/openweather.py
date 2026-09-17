from __future__ import annotations

import os

import requests

from .base import APIResponse, BaseAPI


class OpenWeatherMapAPI(BaseAPI):
    """OpenWeatherMap - Current Weather Data

    Description:
        Returns the current weather conditions (temperature, humidity,
        wind speed, and a short description) for a given city, backed by
        the OpenWeatherMap "Current Weather Data" endpoint.

    Required parameters:
        city (str): City name, optionally "City,CountryCode", e.g.
            "London" or "London,GB".
        api_key (str, optional): Free-tier OpenWeatherMap API key from
            https://openweathermap.org/api. Falls back to the
            OPENWEATHERMAP_API_KEY environment variable if omitted.

    Example response:
        {
            "city": "London",
            "condition": "light rain",
            "temperature_c": 14.2,
            "humidity_pct": 82,
            "wind_speed_ms": 4.6
        }
    """

    name = "openweathermap"
    description = "Returns current weather conditions for a city via OpenWeatherMap."
    parameters = {
        "city": "City name, optionally 'City,CountryCode', e.g. 'London,GB'.",
        "api_key": "OpenWeatherMap API key (optional if OPENWEATHERMAP_API_KEY is set).",
    }

    _ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"

    def call(self, city: str, api_key: str | None = None) -> APIResponse:
        key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")
        if not key:
            return APIResponse(success=False, error="Missing OpenWeatherMap API key.")

        try:
            response = requests.get(
                self._ENDPOINT,
                params={"q": city, "appid": key, "units": "metric"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        data = {
            "city": payload.get("name", city),
            "condition": payload["weather"][0]["description"],
            "temperature_c": payload["main"]["temp"],
            "humidity_pct": payload["main"]["humidity"],
            "wind_speed_ms": payload["wind"]["speed"],
        }
        return APIResponse(success=True, data=data)
