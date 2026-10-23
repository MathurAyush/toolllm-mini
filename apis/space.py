from __future__ import annotations

from datetime import date as _date

from .http import APIError, Param, PublicAPI

_NASA = "https://api.nasa.gov"


class _NasaAPI(PublicAPI):
    # A free personal key from https://api.nasa.gov raises the shared
    # DEMO_KEY limit (30 requests per hour) to 1,000 per hour.
    key_env = "NASA_API_KEY"
    key_default = "DEMO_KEY"


class NasaAPODAPI(_NasaAPI):
    """NASA Astronomy Picture of the Day."""

    name = "nasa_apod"
    category = "space"
    description = (
        "Returns NASA's Astronomy Picture of the Day (space image title, explanation "
        "and image link) for today or a given date."
    )
    params = (Param("date", "string", "Date as YYYY-MM-DD (optional, defaults to today).", required=False),)
    example_call = {"date": "2024-01-15"}
    example_response = {
        "date": "2024-01-15",
        "title": "The Medusa Nebula",
        "explanation": "Braided and serpentine filaments of glowing gas suggest this nebula's popular name.",
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/2401/MedusaNebula_1024.jpg",
        "copyright": "Example Observatory",
    }
    mock_payload = {
        "copyright": "\nExample Observatory\n",
        "date": "2024-01-15",
        "explanation": "Braided and serpentine filaments of glowing gas suggest this nebula's popular name.",
        "hdurl": "https://apod.nasa.gov/apod/image/2401/MedusaNebula.jpg",
        "media_type": "image",
        "service_version": "v1",
        "title": "The Medusa Nebula",
        "url": "https://apod.nasa.gov/apod/image/2401/MedusaNebula_1024.jpg",
    }

    def fetch(self, date):
        params = {"api_key": self.api_key()}
        if date:
            params["date"] = date
        return self.get_json(f"{_NASA}/planetary/apod", params=params)

    def parse(self, payload, date):
        return {
            "date": payload["date"],
            "title": payload["title"],
            "explanation": payload["explanation"].strip(),
            "media_type": payload.get("media_type"),
            "url": payload.get("url"),
            "copyright": (payload.get("copyright") or "").strip() or None,
        }


class NearEarthAsteroidsAPI(_NasaAPI):
    """NASA NeoWs asteroid close approaches for one day."""

    name = "near_earth_asteroids"
    category = "space"
    description = (
        "Lists asteroids passing close to Earth on a date (near-earth objects), with "
        "size, miss distance and whether they are potentially hazardous."
    )
    params = (Param("date", "string", "Date as YYYY-MM-DD (optional, defaults to today).", required=False),)
    example_call = {"date": "2024-01-01"}
    example_response = {
        "date": "2024-01-01",
        "count": 1,
        "asteroids": [
            {
                "name": "(2015 OD22)",
                "diameter_m": [152.2, 340.4],
                "miss_distance_km": 65417380,
                "velocity_kms": 25.39,
                "hazardous": False,
            }
        ],
    }
    mock_payload = {
        "element_count": 1,
        "near_earth_objects": {
            "2024-01-01": [
                {
                    "id": "3724393",
                    "name": "(2015 OD22)",
                    "absolute_magnitude_h": 21.21,
                    "estimated_diameter": {
                        "meters": {"estimated_diameter_min": 152.249185036, "estimated_diameter_max": 340.4395272595}
                    },
                    "is_potentially_hazardous_asteroid": False,
                    "close_approach_data": [
                        {
                            "close_approach_date": "2024-01-01",
                            "relative_velocity": {"kilometers_per_second": "25.3931645932"},
                            "miss_distance": {"kilometers": "65417380.109699369"},
                            "orbiting_body": "Earth",
                        }
                    ],
                }
            ]
        },
    }

    def fetch(self, date):
        day = date or _date.today().isoformat()
        return self.get_json(
            f"{_NASA}/neo/rest/v1/feed",
            params={"start_date": day, "end_date": day, "api_key": self.api_key()},
        )

    def parse(self, payload, date):
        by_day = payload.get("near_earth_objects") or {}
        if not by_day:
            raise APIError("No near-earth object data returned.")
        day = date if date in by_day else next(iter(by_day))
        asteroids = []
        for neo in by_day[day]:
            approach = neo["close_approach_data"][0]
            size = neo["estimated_diameter"]["meters"]
            asteroids.append(
                {
                    "name": neo["name"],
                    "diameter_m": [round(size["estimated_diameter_min"], 1), round(size["estimated_diameter_max"], 1)],
                    "miss_distance_km": round(float(approach["miss_distance"]["kilometers"])),
                    "velocity_kms": round(float(approach["relative_velocity"]["kilometers_per_second"]), 2),
                    "hazardous": neo["is_potentially_hazardous_asteroid"],
                }
            )
        asteroids.sort(key=lambda a: a["miss_distance_km"])
        return {"date": day, "count": len(asteroids), "asteroids": asteroids}


class ISSLocationAPI(PublicAPI):
    """wheretheiss.at live ISS position. No key."""

    name = "iss_location"
    category = "space"
    description = (
        "Returns where the International Space Station (ISS) is right now: its "
        "latitude, longitude, altitude and speed."
    )
    params = ()
    example_call = {}
    example_response = {
        "latitude": 8.4173,
        "longitude": -86.1894,
        "altitude_km": 418.3,
        "velocity_kmh": 27586,
        "visibility": "eclipsed",
        "timestamp": 1792734626,
    }
    mock_payload = {
        "name": "iss",
        "id": 25544,
        "latitude": 8.4172970581805,
        "longitude": -86.18943080827,
        "altitude": 418.32659695635,
        "velocity": 27586.34988186,
        "visibility": "eclipsed",
        "timestamp": 1792734626,
        "units": "kilometers",
    }

    def fetch(self):
        return self.get_json("https://api.wheretheiss.at/v1/satellites/25544")

    def parse(self, payload):
        return {
            "latitude": round(payload["latitude"], 4),
            "longitude": round(payload["longitude"], 4),
            "altitude_km": round(payload["altitude"], 1),
            "velocity_kmh": round(payload["velocity"]),
            "visibility": payload.get("visibility"),
            "timestamp": payload["timestamp"],
        }


class SpaceflightNewsAPI(PublicAPI):
    """Spaceflight News API v4 articles. No key."""

    name = "spaceflight_news"
    category = "space"
    description = "Returns the latest spaceflight and space exploration news articles (rockets, launches, NASA, SpaceX), optionally about a topic."
    params = (
        Param("topic", "string", "Keyword to search for, e.g. 'mars' (optional).", required=False),
        Param("limit", "integer", "Number of articles, 1 to 10 (optional, defaults to 3).", required=False, default=3),
    )
    example_call = {"topic": "mars", "limit": 1}
    example_response = {
        "total": 1831,
        "articles": [
            {
                "title": "MMX Lifts Off on Mission to Explore Moons of Mars",
                "site": "Space Scout",
                "published_at": "2026-10-22T12:08:43Z",
                "summary": "The five-year mission will return samples from Mars' moon Phobos.",
                "url": "https://www.spacescout.info/2026/10/mmx-lifts-off-on-mission-to-explore-moons-of-mars/",
            }
        ],
    }
    mock_payload = {
        "count": 1831,
        "next": "https://api.spaceflightnewsapi.net/v4/articles/?limit=1&offset=1&search=mars",
        "previous": None,
        "results": [
            {
                "id": 40528,
                "title": "MMX Lifts Off on Mission to Explore Moons of Mars",
                "url": "https://www.spacescout.info/2026/10/mmx-lifts-off-on-mission-to-explore-moons-of-mars/",
                "news_site": "Space Scout",
                "summary": "The five-year mission will return samples from Mars' moon Phobos.",
                "published_at": "2026-10-22T12:08:43Z",
            }
        ],
    }

    def fetch(self, topic, limit):
        params = {"limit": max(1, min(limit, 10))}
        if topic:
            params["search"] = topic
        return self.get_json("https://api.spaceflightnewsapi.net/v4/articles/", params=params)

    def parse(self, payload, topic, limit):
        return {
            "total": payload.get("count", 0),
            "articles": [
                {
                    "title": a["title"],
                    "site": a.get("news_site"),
                    "published_at": a.get("published_at"),
                    "summary": a.get("summary"),
                    "url": a.get("url"),
                }
                for a in payload.get("results", [])[:limit]
            ],
        }
