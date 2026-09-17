from __future__ import annotations

import requests

from .base import APIResponse, BaseAPI


class CurrencyExchangeAPI(BaseAPI):
    """Frankfurter - Currency Exchange Rates

    Description:
        Converts an amount from one currency to another using daily
        reference exchange rates published by the European Central Bank.
        No authentication or API key is required.

    Required parameters:
        base (str): Three-letter source currency code, e.g. "USD".
        target (str): Three-letter target currency code, e.g. "EUR".
        amount (float, optional): Amount to convert. Defaults to 1.0.

    Example response:
        {
            "base": "USD",
            "target": "EUR",
            "amount": 1.0,
            "rate": 0.9231,
            "converted": 0.9231
        }
    """

    name = "currency_exchange"
    description = "Converts an amount between currencies using daily exchange rates."
    parameters = {
        "base": "Three-letter source currency code, e.g. 'USD'.",
        "target": "Three-letter target currency code, e.g. 'EUR'.",
        "amount": "Amount to convert (optional, defaults to 1.0).",
    }

    _ENDPOINT = "https://api.frankfurter.app/latest"

    def call(self, base: str, target: str, amount: float = 1.0) -> APIResponse:
        try:
            response = requests.get(
                self._ENDPOINT,
                params={"from": base, "to": target, "amount": amount},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return APIResponse(success=False, error=str(exc))

        converted = payload.get("rates", {}).get(target)
        if converted is None:
            return APIResponse(success=False, error=f"No rate found for '{target}'.")

        data = {
            "base": base,
            "target": target,
            "amount": amount,
            "rate": converted / amount if amount else converted,
            "converted": converted,
        }
        return APIResponse(success=True, data=data)
