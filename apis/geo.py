from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from .http import APIError, Param, PublicAPI

_OPEN_METEO = "https://api.open-meteo.com/v1"

_LAT = Param("latitude", "number", "Latitude in decimal degrees, e.g. 52.52.")
_LON = Param("longitude", "number", "Longitude in decimal degrees, e.g. 13.41.")


class GeocodeAPI(PublicAPI):
    """Open-Meteo Geocoding: place name to coordinates. No key."""

    name = "geocode"
    category = "geo"
    description = (
        "Finds the latitude and longitude coordinates of a city or place name, "
        "with its country, timezone and population."
    )
    params = (Param("place", "string", "City or place name, e.g. 'Berlin'."),)
    example_call = {"place": "Berlin"}
    example_response = {
        "name": "Berlin",
        "country": "Germany",
        "admin_region": "State of Berlin",
        "latitude": 52.52437,
        "longitude": 13.41053,
        "timezone": "Europe/Berlin",
        "population": 3426354,
    }
    mock_payload = {
        "results": [
            {
                "id": 2950159,
                "name": "Berlin",
                "latitude": 52.52437,
                "longitude": 13.41053,
                "elevation": 74.0,
                "country_code": "DE",
                "timezone": "Europe/Berlin",
                "population": 3426354,
                "country": "Germany",
                "admin1": "State of Berlin",
            }
        ],
        "generationtime_ms": 0.127,
    }

    def fetch(self, place):
        return self.get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1, "language": "en", "format": "json"},
        )

    def parse(self, payload, place):
        results = payload.get("results") or []
        if not results:
            raise APIError(f"No place found matching '{place}'.")
        hit = results[0]
        return {
            "name": hit["name"],
            "country": hit.get("country"),
            "admin_region": hit.get("admin1"),
            "latitude": hit["latitude"],
            "longitude": hit["longitude"],
            "timezone": hit.get("timezone"),
            "population": hit.get("population"),
        }


class WeatherForecastAPI(PublicAPI):
    """Open-Meteo daily forecast by coordinates. No key."""

    name = "weather_forecast"
    category = "weather"
    description = (
        "Returns the daily weather forecast (high and low temperature, rain or "
        "precipitation) for the coming days at a latitude and longitude."
    )
    params = (
        _LAT,
        _LON,
        Param("days", "integer", "Number of forecast days, 1 to 16 (optional, defaults to 3).", required=False, default=3),
    )
    example_call = {"latitude": 52.52, "longitude": 13.41, "days": 2}
    example_response = {
        "timezone": "Europe/Berlin",
        "days": [
            {"date": "2026-10-23", "temp_max_c": 14.0, "temp_min_c": 6.2, "precipitation_mm": 0.0},
            {"date": "2026-10-24", "temp_max_c": 11.1, "temp_min_c": 7.1, "precipitation_mm": 6.2},
        ],
    }
    mock_payload = {
        "latitude": 52.512604,
        "longitude": 13.419517,
        "utc_offset_seconds": 7200,
        "timezone": "Europe/Berlin",
        "daily_units": {"time": "iso8601", "temperature_2m_max": "°C", "temperature_2m_min": "°C", "precipitation_sum": "mm"},
        "daily": {
            "time": ["2026-10-23", "2026-10-24"],
            "temperature_2m_max": [14.0, 11.1],
            "temperature_2m_min": [6.2, 7.1],
            "precipitation_sum": [0.0, 6.2],
        },
    }

    def fetch(self, latitude, longitude, days):
        if not 1 <= days <= 16:
            raise APIError("'days' must be between 1 and 16.")
        return self.get_json(
            f"{_OPEN_METEO}/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": days,
            },
        )

    def parse(self, payload, latitude, longitude, days):
        daily = payload["daily"]
        rows = zip(daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["precipitation_sum"])
        return {
            "timezone": payload.get("timezone"),
            "days": [
                {"date": date, "temp_max_c": high, "temp_min_c": low, "precipitation_mm": rain}
                for date, high, low, rain in list(rows)[:days]
            ],
        }


class AirQualityAPI(PublicAPI):
    """Open-Meteo air quality by coordinates. No key."""

    name = "air_quality"
    category = "weather"
    description = (
        "Returns the current air quality index (US AQI) and PM2.5 / PM10 "
        "pollution levels at a latitude and longitude."
    )
    params = (_LAT, _LON)
    example_call = {"latitude": 52.52, "longitude": 13.41}
    example_response = {"time": "2026-10-23T05:00", "us_aqi": 38, "pm2_5_ugm3": 9.0, "pm10_ugm3": 12.4}
    mock_payload = {
        "latitude": 52.5,
        "longitude": 13.400002,
        "timezone": "GMT",
        "current_units": {"time": "iso8601", "interval": "seconds", "pm10": "μg/m³", "pm2_5": "μg/m³", "us_aqi": "USAQI"},
        "current": {"time": "2026-10-23T05:00", "interval": 3600, "pm10": 12.4, "pm2_5": 9.0, "us_aqi": 38},
    }

    def fetch(self, latitude, longitude):
        return self.get_json(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={"latitude": latitude, "longitude": longitude, "current": "pm10,pm2_5,us_aqi"},
        )

    def parse(self, payload, latitude, longitude):
        current = payload["current"]
        return {
            "time": current["time"],
            "us_aqi": current["us_aqi"],
            "pm2_5_ugm3": current["pm2_5"],
            "pm10_ugm3": current["pm10"],
        }


class ElevationAPI(PublicAPI):
    """Open-Meteo elevation model lookup. No key."""

    name = "elevation"
    category = "geo"
    description = "Returns the elevation (altitude above sea level, in meters) of a latitude and longitude."
    params = (_LAT, _LON)
    example_call = {"latitude": 27.98, "longitude": 86.92}
    example_response = {"latitude": 27.98, "longitude": 86.92, "elevation_m": 7533.0}
    mock_payload = {"elevation": [7533.0]}

    def fetch(self, latitude, longitude):
        return self.get_json(f"{_OPEN_METEO}/elevation", params={"latitude": latitude, "longitude": longitude})

    def parse(self, payload, latitude, longitude):
        return {"latitude": latitude, "longitude": longitude, "elevation_m": payload["elevation"][0]}


class ZipCodeAPI(PublicAPI):
    """Zippopotam.us postal code lookup. No key."""

    name = "zip_code_lookup"
    category = "geo"
    description = "Looks up the town, state and coordinates for a postal code or ZIP code in a given country."
    params = (
        Param("postal_code", "string", "Postal or ZIP code, e.g. '90210'."),
        Param("country_code", "string", "Two-letter country code, e.g. 'us' (optional, defaults to 'us').", required=False, default="us"),
    )
    example_call = {"postal_code": "90210", "country_code": "us"}
    example_response = {
        "postal_code": "90210",
        "country": "United States",
        "places": [
            {"name": "Beverly Hills", "state": "California", "latitude": 34.0901, "longitude": -118.4065}
        ],
    }
    mock_payload = {
        "post code": "90210",
        "country": "United States",
        "country abbreviation": "US",
        "places": [
            {
                "place name": "Beverly Hills",
                "longitude": "-118.4065",
                "state": "California",
                "state abbreviation": "CA",
                "latitude": "34.0901",
            }
        ],
    }

    def fetch(self, postal_code, country_code):
        return self.get_json(f"https://api.zippopotam.us/{quote(country_code.lower(), safe='')}/{quote(postal_code, safe='')}")

    def parse(self, payload, postal_code, country_code):
        return {
            "postal_code": payload["post code"],
            "country": payload["country"],
            "places": [
                {
                    "name": place["place name"],
                    "state": place.get("state"),
                    "latitude": float(place["latitude"]),
                    "longitude": float(place["longitude"]),
                }
                for place in payload["places"]
            ],
        }


class IPGeolocationAPI(PublicAPI):
    """ipwho.is IP address geolocation. No key."""

    name = "ip_geolocation"
    category = "geo"
    description = (
        "Looks up the approximate location (city, country), timezone and network "
        "provider (ISP) of an IP address."
    )
    params = (Param("ip", "string", "IPv4 or IPv6 address, e.g. '8.8.8.8'."),)
    example_call = {"ip": "8.8.8.8"}
    example_response = {
        "ip": "8.8.8.8",
        "city": "San Jose",
        "region": "California",
        "country": "United States",
        "latitude": 37.3393939,
        "longitude": -121.8949553,
        "timezone": "America/Los_Angeles",
        "isp": "Google LLC",
    }
    mock_payload = {
        "ip": "8.8.8.8",
        "success": True,
        "type": "IPv4",
        "continent": "North America",
        "country": "United States",
        "country_code": "US",
        "region": "California",
        "city": "San Jose",
        "latitude": 37.3393939,
        "longitude": -121.8949553,
        "connection": {"asn": 15169, "org": "Google LLC", "isp": "Google LLC", "domain": "google.com"},
        "timezone": {"id": "America/Los_Angeles", "abbr": "PDT", "utc": "-07:00"},
    }

    def fetch(self, ip):
        return self.get_json(f"https://ipwho.is/{quote(ip, safe='')}")

    def parse(self, payload, ip):
        if not payload.get("success", False):
            raise APIError(payload.get("message") or f"Could not locate IP address '{ip}'.")
        return {
            "ip": payload["ip"],
            "city": payload.get("city"),
            "region": payload.get("region"),
            "country": payload.get("country"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "timezone": (payload.get("timezone") or {}).get("id"),
            "isp": (payload.get("connection") or {}).get("isp"),
        }


class RecentEarthquakesAPI(PublicAPI):
    """USGS earthquake catalog. No key."""

    name = "recent_earthquakes"
    category = "science"
    description = "Lists the most recent earthquakes worldwide above a minimum magnitude, with location, date and depth."
    params = (
        Param("min_magnitude", "number", "Minimum magnitude (optional, defaults to 4.5).", required=False, default=4.5),
        Param("limit", "integer", "How many earthquakes to return, 1 to 20 (optional, defaults to 5).", required=False, default=5),
    )
    example_call = {"min_magnitude": 5, "limit": 1}
    example_response = [
        {
            "magnitude": 5,
            "place": "153 km S of Kokopo, Papua New Guinea",
            "time_utc": "2026-10-21T19:25:04Z",
            "depth_km": 10,
            "tsunami": False,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000u473",
        }
    ]
    mock_payload = {
        "type": "FeatureCollection",
        "metadata": {"title": "USGS Earthquakes", "status": 200, "count": 1},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "mag": 5,
                    "place": "153 km S of Kokopo, Papua New Guinea",
                    "time": 1792610704207,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000u473",
                    "tsunami": 0,
                    "type": "earthquake",
                    "title": "M 5.0 - 153 km S of Kokopo, Papua New Guinea",
                },
                "geometry": {"type": "Point", "coordinates": [152.2646, -5.728, 10]},
                "id": "us6000u473",
            }
        ],
    }

    def fetch(self, min_magnitude, limit):
        return self.get_json(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={"format": "geojson", "orderby": "time", "minmagnitude": min_magnitude, "limit": max(1, min(limit, 20))},
        )

    def parse(self, payload, min_magnitude, limit):
        quakes = []
        for feature in payload["features"][:limit]:
            props = feature["properties"]
            when = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc)
            quakes.append(
                {
                    "magnitude": props["mag"],
                    "place": props["place"],
                    "time_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "depth_km": feature["geometry"]["coordinates"][2],
                    "tsunami": bool(props.get("tsunami")),
                    "url": props.get("url"),
                }
            )
        return quakes
