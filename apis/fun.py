from __future__ import annotations

import html
from urllib.parse import quote

from .http import APIError, Param, PublicAPI

# Open Trivia DB category ids for the named categories it supports.
TRIVIA_CATEGORIES = {
    "general": 9,
    "books": 10,
    "film": 11,
    "music": 12,
    "television": 14,
    "video games": 15,
    "science": 17,
    "computers": 18,
    "mathematics": 19,
    "mythology": 20,
    "sports": 21,
    "geography": 22,
    "history": 23,
    "politics": 24,
    "art": 25,
    "animals": 27,
    "vehicles": 28,
}


class TriviaQuestionsAPI(PublicAPI):
    """Open Trivia Database quiz questions. No key."""

    name = "trivia_questions"
    category = "trivia"
    description = "Returns trivia quiz questions with the correct answer, by topic and difficulty, for a quiz game."
    params = (
        Param("amount", "integer", "Number of questions, 1 to 10 (optional, defaults to 3).", required=False, default=3),
        Param("topic", "string", "Quiz topic (optional, any topic if omitted).", required=False, enum=tuple(TRIVIA_CATEGORIES)),
        Param("difficulty", "string", "Question difficulty (optional).", required=False, enum=("easy", "medium", "hard")),
    )
    example_call = {"amount": 1, "topic": "science", "difficulty": "easy"}
    example_response = [
        {
            "category": "Science & Nature",
            "difficulty": "easy",
            "question": "What is the chemical symbol for the element oxygen?",
            "correct_answer": "O",
            "options": ["He", "O", "Om", "Ox"],
        }
    ]
    mock_payload = {
        "response_code": 0,
        "results": [
            {
                "type": "multiple",
                "difficulty": "easy",
                "category": "Science &amp; Nature",
                "question": "What is the chemical symbol for the element oxygen?",
                "correct_answer": "O",
                "incorrect_answers": ["He", "Ox", "Om"],
            }
        ],
    }

    def fetch(self, amount, topic, difficulty):
        params = {"amount": max(1, min(amount, 10))}
        if topic:
            params["category"] = TRIVIA_CATEGORIES[topic]
        if difficulty:
            params["difficulty"] = difficulty
        return self.get_json("https://opentdb.com/api.php", params=params)

    def parse(self, payload, amount, topic, difficulty):
        code = payload.get("response_code", 0)
        if code == 5:
            raise APIError("trivia_questions: rate limit reached, wait a few seconds and try again.")
        if code != 0 or not payload.get("results"):
            raise APIError("trivia_questions: no questions available for that topic and difficulty.")
        questions = []
        for q in payload["results"][:amount]:
            answer = html.unescape(q["correct_answer"])
            options = sorted([answer, *(html.unescape(a) for a in q["incorrect_answers"])])
            questions.append(
                {
                    "category": html.unescape(q["category"]),
                    "difficulty": q["difficulty"],
                    "question": html.unescape(q["question"]),
                    "correct_answer": answer,
                    "options": options,
                }
            )
        return questions


class PokemonAPI(PublicAPI):
    """PokeAPI Pokemon data. No key."""

    name = "pokemon_info"
    category = "games"
    description = "Looks up a Pokemon by name or Pokedex number: its types, abilities, height, weight and base stats."
    params = (Param("pokemon", "string", "Pokemon name or Pokedex number, e.g. 'pikachu' or '25'."),)
    example_call = {"pokemon": "pikachu"}
    example_response = {
        "id": 25,
        "name": "pikachu",
        "types": ["electric"],
        "abilities": ["static", "lightning-rod"],
        "height_m": 0.4,
        "weight_kg": 6.0,
        "base_stats": {"hp": 35, "attack": 55, "defense": 40, "special-attack": 50, "special-defense": 50, "speed": 90},
    }
    mock_payload = {
        "id": 25,
        "name": "pikachu",
        "base_experience": 112,
        "height": 4,
        "weight": 60,
        "abilities": [
            {"is_hidden": False, "slot": 1, "ability": {"name": "static", "url": "https://pokeapi.co/api/v2/ability/9/"}},
            {"is_hidden": True, "slot": 3, "ability": {"name": "lightning-rod", "url": "https://pokeapi.co/api/v2/ability/31/"}},
        ],
        "types": [{"slot": 1, "type": {"name": "electric", "url": "https://pokeapi.co/api/v2/type/13/"}}],
        "stats": [
            {"base_stat": 35, "effort": 0, "stat": {"name": "hp"}},
            {"base_stat": 55, "effort": 0, "stat": {"name": "attack"}},
            {"base_stat": 40, "effort": 0, "stat": {"name": "defense"}},
            {"base_stat": 50, "effort": 0, "stat": {"name": "special-attack"}},
            {"base_stat": 50, "effort": 0, "stat": {"name": "special-defense"}},
            {"base_stat": 90, "effort": 2, "stat": {"name": "speed"}},
        ],
    }

    def fetch(self, pokemon):
        return self.get_json(f"https://pokeapi.co/api/v2/pokemon/{quote(pokemon.strip().lower(), safe='')}")

    def parse(self, payload, pokemon):
        return {
            "id": payload["id"],
            "name": payload["name"],
            "types": [t["type"]["name"] for t in payload["types"]],
            "abilities": [a["ability"]["name"] for a in payload["abilities"]],
            # PokeAPI reports height in decimetres and weight in hectograms.
            "height_m": payload["height"] / 10,
            "weight_kg": payload["weight"] / 10,
            "base_stats": {s["stat"]["name"]: s["base_stat"] for s in payload["stats"]},
        }


class AdviceAPI(PublicAPI):
    """Advice Slip random advice. No key."""

    name = "advice"
    category = "entertainment"
    description = "Gives a random piece of life advice or a helpful tip."
    params = ()
    example_call = {}
    example_response = {"advice": "One of the top five regrets people have is that they didn't stay in contact with friends."}
    mock_payload = {"slip": {"id": 116, "advice": "One of the top five regrets people have is that they didn't stay in contact with friends."}}

    def fetch(self):
        return self.get_json("https://api.adviceslip.com/advice")

    def parse(self, payload):
        return {"advice": payload["slip"]["advice"]}


class ColorInfoAPI(PublicAPI):
    """The Color API color details by hex code. No key."""

    name = "color_info"
    category = "design"
    description = "Names a color from its hex code and converts it to RGB, HSL and CMYK color values."
    params = (Param("hex", "string", "Hex color code with or without '#', e.g. '0047AB'."),)
    example_call = {"hex": "#0047AB"}
    example_response = {
        "hex": "#0047AB",
        "name": "Cobalt",
        "exact_name_match": True,
        "rgb": "rgb(0, 71, 171)",
        "hsl": "hsl(215, 100%, 34%)",
        "cmyk": "cmyk(100, 58, 0, 33)",
    }
    mock_payload = {
        "hex": {"value": "#0047AB", "clean": "0047AB"},
        "rgb": {"r": 0, "g": 71, "b": 171, "value": "rgb(0, 71, 171)"},
        "hsl": {"h": 215, "s": 100, "l": 34, "value": "hsl(215, 100%, 34%)"},
        "name": {"value": "Cobalt", "closest_named_hex": "#0047AB", "exact_match_name": True, "distance": 0},
        "cmyk": {"c": 100, "m": 58, "y": 0, "k": 33, "value": "cmyk(100, 58, 0, 33)"},
    }

    def fetch(self, hex):
        code = hex.lstrip("#")
        if len(code) not in (3, 6) or any(c not in "0123456789abcdefABCDEF" for c in code):
            raise APIError(f"'{hex}' is not a hex color code like '0047AB'.")
        return self.get_json("https://www.thecolorapi.com/id", params={"hex": code})

    def parse(self, payload, hex):
        return {
            "hex": payload["hex"]["value"],
            "name": payload["name"]["value"],
            "exact_name_match": payload["name"].get("exact_match_name", False),
            "rgb": payload["rgb"]["value"],
            "hsl": payload["hsl"]["value"],
            "cmyk": payload["cmyk"]["value"],
        }


# Datamuse relation codes behind each `relation` option.
_RELATIONS = {
    "rhymes": "rel_rhy",
    "synonyms": "rel_syn",
    "antonyms": "rel_ant",
    "similar_meaning": "ml",
    "sounds_like": "sl",
}


class RelatedWordsAPI(PublicAPI):
    """Datamuse word-finding queries. No key."""

    name = "related_words"
    category = "words"
    description = "Finds words that rhyme with a word, or its synonyms, antonyms, or words with a similar meaning or sound."
    params = (
        Param("word", "string", "The word to start from, e.g. 'happy'."),
        Param("relation", "string", "Kind of related word to find.", enum=tuple(_RELATIONS)),
        Param("limit", "integer", "Maximum number of words (optional, defaults to 10).", required=False, default=10),
    )
    example_call = {"word": "happy", "relation": "synonyms", "limit": 3}
    example_response = {"word": "happy", "relation": "synonyms", "words": ["glad", "felicitous", "well-chosen"]}
    mock_payload = [
        {"word": "glad", "score": 1381},
        {"word": "felicitous", "score": 1094},
        {"word": "well-chosen", "score": 532},
    ]

    def fetch(self, word, relation, limit):
        return self.get_json(
            "https://api.datamuse.com/words",
            params={_RELATIONS[relation]: word, "max": max(1, min(limit, 50))},
        )

    def parse(self, payload, word, relation, limit):
        return {"word": word, "relation": relation, "words": [w["word"] for w in payload[:limit]]}


class HackerNewsSearchAPI(PublicAPI):
    """Hacker News search via Algolia. No key."""

    name = "hacker_news_search"
    category = "tech"
    description = "Searches Hacker News for technology and programming stories about a topic, with points and comment counts."
    params = (
        Param("query", "string", "Search terms, e.g. 'rust'."),
        Param("limit", "integer", "Number of stories, 1 to 20 (optional, defaults to 5).", required=False, default=5),
    )
    example_call = {"query": "rust", "limit": 1}
    example_response = {
        "total": 60948,
        "stories": [
            {
                "title": "Why Discord is switching from Go to Rust",
                "url": "https://blog.discordapp.com/why-discord-is-switching-from-go-to-rust-a190bbca2b1f",
                "points": 1582,
                "comments": 642,
                "author": "Sikul",
                "created_at": "2020-02-04T17:30:40Z",
                "discussion": "https://news.ycombinator.com/item?id=22238335",
            }
        ],
    }
    mock_payload = {
        "nbHits": 60948,
        "hits": [
            {
                "title": "Why Discord is switching from Go to Rust",
                "url": "https://blog.discordapp.com/why-discord-is-switching-from-go-to-rust-a190bbca2b1f",
                "author": "Sikul",
                "points": 1582,
                "num_comments": 642,
                "created_at": "2020-02-04T17:30:40Z",
                "objectID": "22238335",
            }
        ],
    }

    def fetch(self, query, limit):
        return self.get_json(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "story", "hitsPerPage": max(1, min(limit, 20))},
        )

    def parse(self, payload, query, limit):
        return {
            "total": payload.get("nbHits", 0),
            "stories": [
                {
                    "title": hit.get("title"),
                    "url": hit.get("url"),
                    "points": hit.get("points"),
                    "comments": hit.get("num_comments"),
                    "author": hit.get("author"),
                    "created_at": hit.get("created_at"),
                    "discussion": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                }
                for hit in payload.get("hits", [])[:limit]
            ],
        }
