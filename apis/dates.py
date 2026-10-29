from __future__ import annotations

from datetime import date
from urllib.parse import quote

from .http import APIError, Param, PublicAPI

_COUNTRY = Param("country_code", "string", "Two-letter ISO country code, e.g. 'DE' or 'US'.")
_YEAR = Param("year", "integer", "Year, e.g. 2025 (optional, defaults to the current year).", required=False)


def _year(year: int | None) -> int:
    return year if year is not None else date.today().year


class WorldTimeAPI(PublicAPI):
    """timeapi.io current local time by IANA time zone. No key."""

    name = "world_time"
    category = "clock"
    description = (
        "Returns what the clock reads now (local hour and minute), the date and weekday in a "
        "city's timezone, such as 'Asia/Tokyo' or 'America/New_York'."
    )
    params = (Param("timezone", "string", "IANA time zone name, e.g. 'Asia/Tokyo'."),)
    example_call = {"timezone": "Asia/Tokyo"}
    example_response = {
        "timezone": "Asia/Tokyo",
        "date": "2026-10-23",
        "time": "14:50",
        "day_of_week": "Friday",
        "dst_active": False,
    }
    mock_payload = {
        "year": 2026,
        "month": 10,
        "day": 23,
        "hour": 14,
        "minute": 50,
        "seconds": 4,
        "milliSeconds": 328,
        "dateTime": "2026-10-23T14:50:04.3286451",
        "date": "10/23/2026",
        "time": "14:50",
        "timeZone": "Asia/Tokyo",
        "dayOfWeek": "Friday",
        "dstActive": False,
    }

    def fetch(self, timezone):
        return self.get_json("https://timeapi.io/api/time/current/zone", params={"timeZone": timezone})

    def parse(self, payload, timezone):
        return {
            "timezone": payload["timeZone"],
            "date": f"{payload['year']:04d}-{payload['month']:02d}-{payload['day']:02d}",
            "time": payload["time"],
            "day_of_week": payload["dayOfWeek"],
            "dst_active": payload["dstActive"],
        }


class SunriseSunsetAPI(PublicAPI):
    """sunrise-sunset.org solar times by coordinates. No key."""

    name = "sunrise_sunset"
    category = "calendar"
    description = "Returns sunrise, sunset and day length (in UTC) on a date at a latitude and longitude."
    params = (
        Param("latitude", "number", "Latitude in decimal degrees, e.g. 48.85."),
        Param("longitude", "number", "Longitude in decimal degrees, e.g. 2.35."),
        Param("date", "string", "Date as YYYY-MM-DD (optional, defaults to today).", required=False, default="today"),
    )
    example_call = {"latitude": 48.85, "longitude": 2.35, "date": "2025-06-21"}
    example_response = {
        "date": "2025-06-21",
        "sunrise_utc": "2025-06-21T03:47:01+00:00",
        "sunset_utc": "2025-06-21T19:57:55+00:00",
        "solar_noon_utc": "2025-06-21T11:52:28+00:00",
        "day_length_hours": 16.18,
    }
    mock_payload = {
        "results": {
            "sunrise": "2025-06-21T03:47:01+00:00",
            "sunset": "2025-06-21T19:57:55+00:00",
            "solar_noon": "2025-06-21T11:52:28+00:00",
            "day_length": 58254,
            "civil_twilight_begin": "2025-06-21T03:04:28+00:00",
            "civil_twilight_end": "2025-06-21T20:40:29+00:00",
        },
        "status": "OK",
        "tzid": "UTC",
    }

    def fetch(self, latitude, longitude, date):
        return self.get_json(
            "https://api.sunrise-sunset.org/json",
            params={"lat": latitude, "lng": longitude, "date": date, "formatted": 0},
        )

    def parse(self, payload, latitude, longitude, date):
        if payload.get("status") != "OK":
            raise APIError(f"sunrise_sunset: {payload.get('status', 'unknown error')}.")
        results = payload["results"]
        return {
            "date": results["sunrise"][:10],
            "sunrise_utc": results["sunrise"],
            "sunset_utc": results["sunset"],
            "solar_noon_utc": results["solar_noon"],
            "day_length_hours": round(results["day_length"] / 3600, 2),
        }


class PublicHolidaysAPI(PublicAPI):
    """Nager.Date public holidays. No key."""

    name = "public_holidays"
    category = "calendar"
    description = "Lists the official public holidays (bank holidays) of a country in a given year, with dates."
    params = (_COUNTRY, _YEAR)
    example_call = {"country_code": "DE", "year": 2025}
    example_response = {
        "country_code": "DE",
        "year": 2025,
        "holidays": [
            {"date": "2025-01-01", "name": "New Year's Day", "local_name": "Neujahr", "nationwide": True},
            {"date": "2025-04-18", "name": "Good Friday", "local_name": "Karfreitag", "nationwide": True},
            {"date": "2025-10-03", "name": "German Unity Day", "local_name": "Tag der Deutschen Einheit", "nationwide": True},
        ],
    }
    mock_payload = [
        {"date": "2025-01-01", "localName": "Neujahr", "name": "New Year's Day", "countryCode": "DE", "fixed": False, "global": True, "counties": None, "types": ["Public"]},
        {"date": "2025-04-18", "localName": "Karfreitag", "name": "Good Friday", "countryCode": "DE", "fixed": False, "global": True, "counties": None, "types": ["Public"]},
        {"date": "2025-10-03", "localName": "Tag der Deutschen Einheit", "name": "German Unity Day", "countryCode": "DE", "fixed": False, "global": True, "counties": None, "types": ["Public"]},
    ]

    def fetch(self, country_code, year):
        return self.get_json(f"https://date.nager.at/api/v3/PublicHolidays/{_year(year)}/{quote(country_code.upper(), safe='')}")

    def parse(self, payload, country_code, year):
        return {
            "country_code": country_code.upper(),
            "year": _year(year),
            "holidays": [
                {"date": h["date"], "name": h["name"], "local_name": h["localName"], "nationwide": h["global"]}
                for h in payload
            ],
        }


class LongWeekendsAPI(PublicAPI):
    """Nager.Date long weekends. No key."""

    name = "long_weekends"
    category = "calendar"
    description = (
        "Lists the long weekends of a year in a country (public holidays next to a "
        "weekend), including any bridge days to take off for a vacation."
    )
    params = (_COUNTRY, _YEAR)
    example_call = {"country_code": "DE", "year": 2025}
    example_response = [
        {"start": "2025-04-18", "end": "2025-04-21", "days": 4, "bridge_days": []},
        {"start": "2025-05-01", "end": "2025-05-04", "days": 4, "bridge_days": ["2025-05-02"]},
    ]
    mock_payload = [
        {"startDate": "2025-04-18", "endDate": "2025-04-21", "dayCount": 4, "needBridgeDay": False, "bridgeDays": []},
        {"startDate": "2025-05-01", "endDate": "2025-05-04", "dayCount": 4, "needBridgeDay": True, "bridgeDays": ["2025-05-02"]},
    ]

    def fetch(self, country_code, year):
        return self.get_json(f"https://date.nager.at/api/v3/LongWeekend/{_year(year)}/{quote(country_code.upper(), safe='')}")

    def parse(self, payload, country_code, year):
        return [
            {"start": w["startDate"], "end": w["endDate"], "days": w["dayCount"], "bridge_days": w.get("bridgeDays") or []}
            for w in payload
        ]
