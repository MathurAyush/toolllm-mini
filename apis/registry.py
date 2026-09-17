from __future__ import annotations

from .base import BaseAPI
from .calculator import CalculatorAPI
from .search import SearchAPI
from .weather import WeatherAPI


class APIRegistry:
    def __init__(self) -> None:
        self._apis: dict[str, BaseAPI] = {}

    def register(self, api: BaseAPI) -> None:
        self._apis[api.name] = api

    def get(self, name: str) -> BaseAPI | None:
        return self._apis.get(name)

    def all(self) -> list[BaseAPI]:
        return list(self._apis.values())


def default_registry() -> APIRegistry:
    registry = APIRegistry()
    registry.register(CalculatorAPI())
    registry.register(WeatherAPI())
    registry.register(SearchAPI())
    return registry
