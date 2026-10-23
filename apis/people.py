from __future__ import annotations

from urllib.parse import quote

from .http import APIError, Param, PublicAPI

_FIRST_NAME = Param("name", "string", "A first name, e.g. 'Michael'.")


class RandomUserAPI(PublicAPI):
    """randomuser.me fake user profiles. No key."""

    name = "random_user"
    category = "people"
    description = (
        "Generates random fake user profiles (name, email, phone, age, address) "
        "for test data or placeholder people."
    )
    params = (
        Param("count", "integer", "Number of users, 1 to 10 (optional, defaults to 1).", required=False, default=1),
        Param("nationality", "string", "Nationality code, e.g. 'us', 'gb', 'fr' (optional).", required=False),
    )
    example_call = {"count": 1, "nationality": "us"}
    example_response = [
        {
            "name": "Tara Holland",
            "gender": "female",
            "email": "tara.holland@example.com",
            "phone": "(639) 258-8517",
            "age": 39,
            "city": "Chicago",
            "country": "United States",
            "nationality": "US",
        }
    ]
    mock_payload = {
        "results": [
            {
                "gender": "female",
                "name": {"title": "Ms", "first": "Tara", "last": "Holland"},
                "location": {"city": "Chicago", "state": "North Dakota", "country": "United States", "postcode": 17069},
                "email": "tara.holland@example.com",
                "dob": {"date": "1986-11-01T09:33:09.254Z", "age": 39},
                "phone": "(639) 258-8517",
                "nat": "US",
            }
        ]
    }

    def fetch(self, count, nationality):
        params = {"results": max(1, min(count, 10)), "inc": "gender,name,location,email,dob,phone,nat", "noinfo": ""}
        if nationality:
            params["nat"] = nationality.lower()
        return self.get_json("https://randomuser.me/api/", params=params)

    def parse(self, payload, count, nationality):
        if payload.get("error"):
            raise APIError(f"random_user: {payload['error']}")
        return [
            {
                "name": f"{u['name']['first']} {u['name']['last']}",
                "gender": u.get("gender"),
                "email": u.get("email"),
                "phone": u.get("phone"),
                "age": u["dob"]["age"],
                "city": u["location"]["city"],
                "country": u["location"]["country"],
                "nationality": u.get("nat"),
            }
            for u in payload["results"][:count]
        ]


class AgeFromNameAPI(PublicAPI):
    """agify.io age estimate from a first name. No key (100 names/day)."""

    name = "age_from_name"
    category = "people"
    description = "Predicts how old someone named a given first name is likely to be (estimated age), based on statistics."
    params = (_FIRST_NAME, Param("country_code", "string", "Two-letter country code to narrow the estimate (optional).", required=False))
    example_call = {"name": "Michael"}
    example_response = {"name": "michael", "estimated_age": 57, "sample_size": 311558}
    mock_payload = {"count": 311558, "name": "michael", "age": 57}

    def fetch(self, name, country_code):
        params = {"name": name}
        if country_code:
            params["country_id"] = country_code.upper()
        return self.get_json("https://api.agify.io", params=params)

    def parse(self, payload, name, country_code):
        if payload.get("age") is None:
            raise APIError(f"No age estimate available for the name '{name}'.")
        return {"name": payload["name"], "estimated_age": payload["age"], "sample_size": payload.get("count")}


class NationalityFromNameAPI(PublicAPI):
    """nationalize.io country estimate from a name. No key (100 names/day)."""

    name = "nationality_from_name"
    category = "people"
    description = "Predicts which countries a person's name most likely comes from (nationality origin), with probabilities."
    params = (Param("name", "string", "A first or last name, e.g. 'Nathaniel'."),)
    example_call = {"name": "Nathaniel"}
    example_response = {
        "name": "nathaniel",
        "countries": [
            {"country_code": "US", "probability": 0.358},
            {"country_code": "NG", "probability": 0.076},
            {"country_code": "PH", "probability": 0.069},
        ],
    }
    mock_payload = {
        "count": 57823,
        "name": "nathaniel",
        "country": [
            {"country_id": "US", "probability": 0.357622},
            {"country_id": "NG", "probability": 0.07579},
            {"country_id": "PH", "probability": 0.069334},
            {"country_id": "GH", "probability": 0.067883},
        ],
    }

    def fetch(self, name):
        return self.get_json("https://api.nationalize.io", params={"name": name})

    def parse(self, payload, name):
        countries = payload.get("country") or []
        if not countries:
            raise APIError(f"No nationality estimate available for the name '{name}'.")
        return {
            "name": payload["name"],
            "countries": [
                {"country_code": c["country_id"], "probability": round(c["probability"], 3)} for c in countries[:3]
            ],
        }


class UniversitySearchAPI(PublicAPI):
    """Hipo university domains list. No key; the service is HTTP only."""

    name = "university_search"
    category = "education"
    description = "Searches universities and colleges by name and/or country, returning their websites and domains."
    params = (
        Param("name", "string", "Part of the university name, e.g. 'oxford' (optional).", required=False),
        Param("country", "string", "Full country name, e.g. 'United Kingdom' (optional).", required=False),
        Param("limit", "integer", "Maximum number of results (optional, defaults to 5).", required=False, default=5),
    )
    example_call = {"name": "oxford", "country": "United Kingdom"}
    example_response = {
        "total": 2,
        "universities": [
            {"name": "Oxford Brookes University", "country": "United Kingdom", "website": "http://www.brookes.ac.uk/", "domains": ["brookes.ac.uk"]},
            {"name": "University of Oxford", "country": "United Kingdom", "website": "http://www.ox.ac.uk/", "domains": ["oxford.ac.uk", "ox.ac.uk"]},
        ],
    }
    mock_payload = [
        {"state-province": None, "name": "Oxford Brookes University", "web_pages": ["http://www.brookes.ac.uk/"], "alpha_two_code": "GB", "domains": ["brookes.ac.uk"], "country": "United Kingdom"},
        {"state-province": None, "name": "University of Oxford", "web_pages": ["http://www.ox.ac.uk/"], "alpha_two_code": "GB", "domains": ["oxford.ac.uk", "ox.ac.uk"], "country": "United Kingdom"},
    ]

    def fetch(self, name, country, limit):
        if not name and not country:
            raise APIError("Give a university name, a country, or both.")
        params = {k: v for k, v in {"name": name, "country": country}.items() if v}
        return self.get_json("http://universities.hipolabs.com/search", params=params)

    def parse(self, payload, name, country, limit):
        if not payload:
            raise APIError("No universities found.")
        return {
            "total": len(payload),
            "universities": [
                {
                    "name": u["name"],
                    "country": u.get("country"),
                    "website": (u.get("web_pages") or [None])[0],
                    "domains": u.get("domains", []),
                }
                for u in payload[: max(1, limit)]
            ],
        }


class GitHubUserAPI(PublicAPI):
    """GitHub REST user profile. No key needed (60 requests per hour);
    set GITHUB_TOKEN in .env for 5,000 per hour."""

    name = "github_user"
    category = "tech"
    description = "Looks up a GitHub user or organization profile: name, bio, public repositories and followers."
    params = (Param("username", "string", "GitHub login, e.g. 'torvalds'."),)
    key_env = "GITHUB_TOKEN"
    example_call = {"username": "torvalds"}
    example_response = {
        "login": "torvalds",
        "name": "Linus Torvalds",
        "type": "User",
        "company": "Linux Foundation",
        "location": "Portland, OR",
        "bio": None,
        "public_repos": 12,
        "followers": 329059,
        "created_at": "2011-09-03T15:26:22Z",
        "url": "https://github.com/torvalds",
    }
    mock_payload = {
        "login": "torvalds",
        "id": 1024025,
        "type": "User",
        "html_url": "https://github.com/torvalds",
        "name": "Linus Torvalds",
        "company": "Linux Foundation",
        "location": "Portland, OR",
        "bio": None,
        "public_repos": 12,
        "followers": 329059,
        "following": 0,
        "created_at": "2011-09-03T15:26:22Z",
    }

    def fetch(self, username):
        headers = {"Accept": "application/vnd.github+json"}
        token = self.api_key()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.get_json(f"https://api.github.com/users/{quote(username.strip().lstrip('@'))}", headers=headers)

    def parse(self, payload, username):
        return {
            "login": payload["login"],
            "name": payload.get("name"),
            "type": payload.get("type"),
            "company": payload.get("company"),
            "location": payload.get("location"),
            "bio": payload.get("bio"),
            "public_repos": payload.get("public_repos"),
            "followers": payload.get("followers"),
            "created_at": payload.get("created_at"),
            "url": payload.get("html_url"),
        }
