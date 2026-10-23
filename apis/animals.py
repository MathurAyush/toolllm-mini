from __future__ import annotations

from urllib.parse import quote

from .http import APIError, Param, PublicAPI


class CatFactAPI(PublicAPI):
    """catfact.ninja random cat fact. No key."""

    name = "cat_fact"
    category = "animals"
    description = "Returns a random fun fact about cats."
    params = ()
    example_call = {}
    example_response = {"fact": "Cats sweat only through their paws."}
    mock_payload = {"fact": "Cats sweat only through their paws.", "length": 35}

    def fetch(self):
        return self.get_json("https://catfact.ninja/fact")

    def parse(self, payload):
        return {"fact": payload["fact"]}


class DogFactAPI(PublicAPI):
    """dogapi.dog random dog fact. No key."""

    name = "dog_fact"
    category = "animals"
    description = "Returns a random fun fact about dogs."
    params = ()
    example_call = {}
    example_response = {"fact": "The largest dog was an English Mastiff who weighed 343 pounds."}
    mock_payload = {
        "data": [
            {
                "id": "c60e61e1-0ba6-4413-99d0-997a17148ea9",
                "type": "fact",
                "attributes": {"body": "The largest dog was an English Mastiff who weighed 343 pounds."},
            }
        ]
    }

    def fetch(self):
        return self.get_json("https://dogapi.dog/api/v2/facts", params={"limit": 1})

    def parse(self, payload):
        return {"fact": payload["data"][0]["attributes"]["body"]}


class DogImageAPI(PublicAPI):
    """dog.ceo random dog picture. No key."""

    name = "dog_image"
    category = "animals"
    description = "Returns a link to a random photo or picture of a dog, optionally of a specific breed."
    params = (Param("breed", "string", "Dog breed, e.g. 'husky' or 'retriever/golden' (optional).", required=False),)
    example_call = {"breed": "husky"}
    example_response = {"breed": "husky", "image_url": "https://images.dog.ceo/breeds/husky/n02110185_8564.jpg"}
    mock_payload = {"message": "https://images.dog.ceo/breeds/husky/n02110185_8564.jpg", "status": "success"}

    def fetch(self, breed):
        if breed:
            path = "/".join(quote(part) for part in breed.lower().replace(" ", "/").split("/"))
            return self.get_json(f"https://dog.ceo/api/breed/{path}/images/random")
        return self.get_json("https://dog.ceo/api/breeds/image/random")

    def parse(self, payload, breed):
        if payload.get("status") != "success":
            raise APIError(payload.get("message") or "dog_image: request failed.")
        return {"breed": breed, "image_url": payload["message"]}
