from __future__ import annotations

from .base import APIResponse, BaseAPI


class WeatherAPI(BaseAPI):
    name = "weather"
    description = "Returns a mock current-weather report for a given city."
    parameters = {"city": "Name of the city to look up, e.g. 'Paris'."}
    category = "weather"
    example_call = {"city": "Tokyo"}
    example_response = {"condition": "Clear", "temperature_c": 27}

    _MOCK_DATA = {
        "paris": {"condition": "Cloudy", "temperature_c": 18},
        "tokyo": {"condition": "Clear", "temperature_c": 27},
        "new york": {"condition": "Rain", "temperature_c": 21},
    }

    def call(self, city: str) -> APIResponse:
        record = self._MOCK_DATA.get(city.strip().lower())
        if record is None:
            return APIResponse(success=False, error=f"No weather data available for '{city}'.")
        return APIResponse(success=True, data=record)
