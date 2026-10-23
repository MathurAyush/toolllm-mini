from __future__ import annotations

from .http import APIError, Param, PublicAPI

# TheMealDB and TheCocktailDB publish "1" as their free public test key.
_MEALDB = "https://www.themealdb.com/api/json/v1/1"
_COCKTAILDB = "https://www.thecocktaildb.com/api/json/v1/1"


def _ingredients(record: dict, count: int) -> list[str]:
    """Pairs strIngredientN with strMeasureN, skipping the empty slots."""
    items = []
    for i in range(1, count + 1):
        ingredient = (record.get(f"strIngredient{i}") or "").strip()
        if ingredient:
            measure = (record.get(f"strMeasure{i}") or "").strip()
            items.append(f"{measure} {ingredient}".strip())
    return items


def _meal(record: dict) -> dict:
    return {
        "name": record["strMeal"],
        "category": record.get("strCategory"),
        "cuisine": record.get("strArea"),
        "ingredients": _ingredients(record, 20),
        "instructions": (record.get("strInstructions") or "").strip(),
        "source": record.get("strSource") or record.get("strYoutube"),
    }


_ARRABIATA = {
    "idMeal": "52771",
    "strMeal": "Spicy Arrabiata Penne",
    "strCategory": "Vegetarian",
    "strArea": "Italian",
    "strInstructions": "Bring a large pot of water to a boil. Cook the penne, then toss with the spicy tomato sauce.",
    "strIngredient1": "penne rigate",
    "strIngredient2": "olive oil",
    "strIngredient3": "garlic",
    "strIngredient4": "",
    "strIngredient5": None,
    "strMeasure1": "1 pound",
    "strMeasure2": "1/4 cup",
    "strMeasure3": "3 cloves",
    "strMeasure4": "",
    "strMeasure5": None,
    "strSource": None,
    "strYoutube": "https://www.youtube.com/watch?v=1IszT_guI08",
}

_ARRABIATA_RESULT = {
    "name": "Spicy Arrabiata Penne",
    "category": "Vegetarian",
    "cuisine": "Italian",
    "ingredients": ["1 pound penne rigate", "1/4 cup olive oil", "3 cloves garlic"],
    "instructions": "Bring a large pot of water to a boil. Cook the penne, then toss with the spicy tomato sauce.",
    "source": "https://www.youtube.com/watch?v=1IszT_guI08",
}


class RecipeSearchAPI(PublicAPI):
    """TheMealDB recipe search by dish name."""

    name = "recipe_search"
    category = "food"
    description = "Finds cooking recipes for a dish or meal by name, with ingredients and instructions on how to cook it."
    params = (
        Param("dish", "string", "Dish name or part of it, e.g. 'arrabiata' or 'chicken curry'."),
        Param("limit", "integer", "Maximum number of recipes (optional, defaults to 3).", required=False, default=3),
    )
    example_call = {"dish": "arrabiata"}
    example_response = [_ARRABIATA_RESULT]
    mock_payload = {"meals": [_ARRABIATA]}

    def fetch(self, dish, limit):
        return self.get_json(f"{_MEALDB}/search.php", params={"s": dish})

    def parse(self, payload, dish, limit):
        meals = payload.get("meals") or []
        if not meals:
            raise APIError(f"No recipes found for '{dish}'.")
        return [_meal(m) for m in meals[: max(1, limit)]]


class RandomRecipeAPI(PublicAPI):
    """TheMealDB random recipe."""

    name = "random_recipe"
    category = "food"
    description = "Suggests a random recipe idea for what to cook for dinner, with ingredients and instructions."
    params = ()
    example_call = {}
    example_response = _ARRABIATA_RESULT
    mock_payload = {"meals": [_ARRABIATA]}

    def fetch(self):
        return self.get_json(f"{_MEALDB}/random.php")

    def parse(self, payload):
        return _meal(payload["meals"][0])


class CocktailSearchAPI(PublicAPI):
    """TheCocktailDB drink search by name."""

    name = "cocktail_search"
    category = "food"
    description = "Finds cocktail and drink recipes by name, with the glass, ingredients and how to mix them."
    params = (Param("drink", "string", "Cocktail name, e.g. 'margarita'."),)
    example_call = {"drink": "margarita"}
    example_response = [
        {
            "name": "Margarita",
            "alcoholic": True,
            "glass": "Cocktail glass",
            "ingredients": ["1 1/2 oz Tequila", "1/2 oz Triple sec", "1 oz Lime juice", "Salt"],
            "instructions": "Rub the rim of the glass with the lime slice to make the salt stick to it. Shake the other ingredients with ice, then carefully pour into the glass.",
        }
    ]
    mock_payload = {
        "drinks": [
            {
                "idDrink": "11007",
                "strDrink": "Margarita",
                "strCategory": "Ordinary Drink",
                "strAlcoholic": "Alcoholic",
                "strGlass": "Cocktail glass",
                "strInstructions": "Rub the rim of the glass with the lime slice to make the salt stick to it. Shake the other ingredients with ice, then carefully pour into the glass.",
                "strIngredient1": "Tequila",
                "strIngredient2": "Triple sec",
                "strIngredient3": "Lime juice",
                "strIngredient4": "Salt",
                "strIngredient5": None,
                "strMeasure1": "1 1/2 oz ",
                "strMeasure2": "1/2 oz ",
                "strMeasure3": "1 oz ",
                "strMeasure4": None,
                "strMeasure5": None,
            }
        ]
    }

    def fetch(self, drink):
        return self.get_json(f"{_COCKTAILDB}/search.php", params={"s": drink})

    def parse(self, payload, drink):
        drinks = payload.get("drinks") or []
        if not drinks:
            raise APIError(f"No cocktails found for '{drink}'.")
        return [
            {
                "name": d["strDrink"],
                "alcoholic": d.get("strAlcoholic") == "Alcoholic",
                "glass": d.get("strGlass"),
                "ingredients": _ingredients(d, 15),
                "instructions": (d.get("strInstructions") or "").strip(),
            }
            for d in drinks[:3]
        ]
