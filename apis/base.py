from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIResponse:
    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class APISpec:
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)


class BaseAPI(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, str] = {}

    @abstractmethod
    def call(self, **kwargs: Any) -> APIResponse:
        raise NotImplementedError

    def spec(self) -> APISpec:
        return APISpec(name=self.name, description=self.description, parameters=self.parameters)
