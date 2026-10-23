from __future__ import annotations

from .http import APIError, Param, PublicAPI


class HistoricalExchangeRateAPI(PublicAPI):
    """Frankfurter (ECB) exchange rate on a past date. No key."""

    name = "historical_exchange_rate"
    category = "finance"
    description = (
        "Returns the exchange rate between two currencies on a specific past date "
        "(historical rate, from European Central Bank reference data since 1999)."
    )
    params = (
        Param("base", "string", "Three-letter source currency code, e.g. 'USD'."),
        Param("target", "string", "Three-letter target currency code, e.g. 'EUR'."),
        Param("date", "string", "Date as YYYY-MM-DD, e.g. '2020-01-02'."),
    )
    example_call = {"base": "USD", "target": "EUR", "date": "2020-01-02"}
    example_response = {"base": "USD", "target": "EUR", "date": "2020-01-02", "rate": 0.89342}
    mock_payload = {"amount": 1.0, "base": "USD", "date": "2020-01-02", "rates": {"EUR": 0.89342}}

    def fetch(self, base, target, date):
        return self.get_json(
            f"https://api.frankfurter.app/{date}",
            params={"from": base.upper(), "to": target.upper()},
        )

    def parse(self, payload, base, target, date):
        rate = payload.get("rates", {}).get(target.upper())
        if rate is None:
            raise APIError(f"No rate found for '{target}'.")
        # Weekends and holidays resolve to the previous working day.
        return {"base": payload["base"], "target": target.upper(), "date": payload["date"], "rate": rate}


class CryptoPriceAPI(PublicAPI):
    """CoinGecko simple price. No key needed for the public tier."""

    name = "crypto_price"
    category = "finance"
    description = (
        "Returns the current market price of a cryptocurrency such as bitcoin or "
        "ethereum, and its 24 hour change."
    )
    params = (
        Param("coin", "string", "CoinGecko coin id, e.g. 'bitcoin', 'ethereum', 'solana'."),
        Param("vs_currency", "string", "Currency to price in, e.g. 'usd' (optional, defaults to 'usd').", required=False, default="usd"),
    )
    example_call = {"coin": "bitcoin", "vs_currency": "usd"}
    example_response = {"coin": "bitcoin", "vs_currency": "usd", "price": 81670, "change_24h_pct": -1.28}
    mock_payload = {"bitcoin": {"usd": 81670, "usd_24h_change": -1.2753914847638006}}

    def fetch(self, coin, vs_currency):
        return self.get_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin.lower(), "vs_currencies": vs_currency.lower(), "include_24hr_change": "true"},
        )

    def parse(self, payload, coin, vs_currency):
        coin, vs_currency = coin.lower(), vs_currency.lower()
        quote = payload.get(coin)
        if not quote or vs_currency not in quote:
            raise APIError(f"No price found for coin '{coin}' in '{vs_currency}'. Use a CoinGecko id such as 'bitcoin'.")
        change = quote.get(f"{vs_currency}_24h_change")
        return {
            "coin": coin,
            "vs_currency": vs_currency,
            "price": quote[vs_currency],
            "change_24h_pct": round(change, 2) if change is not None else None,
        }
