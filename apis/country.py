from __future__ import annotations

import requests

from .base import APIResponse, BaseAPI


class CountryInfoAPI(BaseAPI):
    """REST Countries - Country Information

    Description:
        Returns key facts about a country (capital, region, population,
        and currencies) by name, via the public REST Countries API. No
        authentication required.

    Required parameters:
        name (str): Country name, common or official, e.g. "Japan".

    Example response:
        {
            "name": "Japan",
            "capital": "Tokyo",
            "region": "Asia",
            "population": 125836021,
            "currencies": ["JPY"]
        }
    """

    name = "country_info"
    description = "Returns capital, region, population, and currency info for a country."
    parameters = {"name": "Country name, e.g. 'Japan'."}

    _ENDPOINT = "https://restcountries.com/v3.1/name/{name}"

    def call(self, name: str) -> APIResponse:
        try:
            response = requests.get(self._ENDPOINT.format(name=name), timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        if not payload:
            return APIResponse(success=False, error=f"No country data found for '{name}'.")

        country = payload[0]
        data = {
            "name": country.get("name", {}).get("common", name),
            "capital": (country.get("capital") or [""])[0],
            "region": country.get("region"),
            "population": country.get("population"),
            "currencies": list(country.get("currencies", {}).keys()),
        }
        return APIResponse(success=True, data=data)
