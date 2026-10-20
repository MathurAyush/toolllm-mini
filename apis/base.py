from __future__ import annotations

import inspect
import types
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Credentials are read from the environment by the API itself; they are never
# exposed to the model as tool parameters.
_HIDDEN_PARAMETERS = {"api_key"}

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


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


def _json_type(annotation: Any) -> str:
    """Maps a Python annotation (e.g. `str`, `float`, `str | None`) to a JSON
    schema type. Optional types map to their non-None member."""
    if isinstance(annotation, types.UnionType) or typing.get_origin(annotation) is typing.Union:
        members = [a for a in typing.get_args(annotation) if a is not type(None)]
        annotation = members[0] if len(members) == 1 else str
    return _JSON_TYPES.get(annotation, "string")


class BaseAPI(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, str] = {}

    @abstractmethod
    def call(self, **kwargs: Any) -> APIResponse:
        raise NotImplementedError

    def spec(self) -> APISpec:
        return APISpec(name=self.name, description=self.description, parameters=self.parameters)

    def function_schema(self) -> dict:
        """Function declaration for native tool calling: the name and
        description from the registry, and a JSON schema whose properties are
        the documented `parameters`, typed from the `call` signature, with
        every parameter that has no default marked as required."""
        # Read from the class so a wrapped or patched instance method (e.g. a
        # test spy) still yields the declared signature.
        signature = inspect.signature(type(self).call)
        hints = typing.get_type_hints(type(self).call)
        properties: dict[str, dict] = {}
        required: list[str] = []
        for name, description in self.parameters.items():
            if name in _HIDDEN_PARAMETERS:
                continue
            properties[name] = {"type": _json_type(hints.get(name, str)), "description": description}
            param = signature.parameters.get(name)
            if param is not None and param.default is inspect.Parameter.empty:
                required.append(name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        }
