from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from .base import APIResponse, BaseAPI

USER_AGENT = "toolllm-mini/1.0 (+https://github.com/MathurAyush/toolllm-mini)"

# Set to 1 to serve every PublicAPI from its recorded mock payload instead of
# the network, e.g. for offline test runs.
OFFLINE_ENV = "TOOLLLM_OFFLINE"

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def offline_mode() -> bool:
    return os.environ.get(OFFLINE_ENV, "").strip().lower() in _TRUE


class APIError(Exception):
    """A request or response problem, reported to the caller as a failed
    APIResponse rather than raised."""


@dataclass(frozen=True)
class Param:
    """One typed tool parameter. `type` is a JSON schema type: "string",
    "integer", "number" or "boolean". Optional parameters take `default`
    when the caller leaves them out."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: tuple[str, ...] | None = None


def _coerce(param: Param, value: Any) -> Any:
    """Converts an argument to the parameter's type. Models often send every
    argument as text, e.g. count="5"."""
    try:
        if param.type == "integer":
            number = float(value)
            if not number.is_integer():
                raise ValueError
            return int(number)
        if param.type == "number":
            return float(value)
        if param.type == "boolean":
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in _TRUE:
                return True
            if text in _FALSE:
                return False
            raise ValueError
    except (TypeError, ValueError):
        article = "an" if param.type == "integer" else "a"
        raise APIError(f"'{param.name}' must be {article} {param.type}, got {value!r}.") from None

    text = str(value).strip()
    if param.enum is not None:
        match = next((option for option in param.enum if option.lower() == text.lower()), None)
        if match is None:
            raise APIError(f"'{param.name}' must be one of {', '.join(param.enum)}, got {value!r}.")
        return match
    return text


class PublicAPI(BaseAPI):
    """Base class for wrappers around free public web APIs.

    A subclass declares its typed `params`, a `category`, an example call
    and the response that call gives, and implements `fetch` (one HTTP
    request through `get_json`) and `parse` (upstream payload to the
    tool's result). `call` validates and coerces the arguments, then
    either fetches live or, in offline mode, parses `mock_payload`, a
    recorded upstream response, so tests run without the network. A live
    failure is reported as an error, never answered from the mock.
    """

    params: tuple[Param, ...] = ()
    mock_payload: Any = None
    timeout: float = 10.0
    # Environment variable holding an optional or required API key; keys
    # are read from the environment (e.g. a local .env file) only.
    key_env: str | None = None
    key_default: str | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.parameters = {p.name: p.description for p in cls.params}

    def __init__(self, offline: bool | None = None) -> None:
        self._offline = offline

    @property
    def offline(self) -> bool:
        return offline_mode() if self._offline is None else self._offline

    def call(self, **kwargs: Any) -> APIResponse:
        try:
            args = self._bind(kwargs)
            payload = self.mock_payload if self.offline else self.fetch(**args)
            data = self.parse(payload, **args)
        except APIError as exc:
            return APIResponse(success=False, error=str(exc))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return APIResponse(success=False, error=f"Unexpected response from {self.name}: {exc!r}")
        return APIResponse(success=True, data=data)

    def fetch(self, **args: Any) -> Any:
        raise NotImplementedError

    def parse(self, payload: Any, **args: Any) -> Any:
        return payload

    def api_key(self) -> str | None:
        if self.key_env is None:
            return None
        return os.environ.get(self.key_env) or self.key_default

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})},
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise APIError(f"{self.name} timed out after {self.timeout:g}s.") from None
        except requests.RequestException as exc:
            raise APIError(f"{self.name} request failed: {exc}") from None

        if response.status_code == 404:
            raise APIError(f"{self.name}: nothing found (HTTP 404).")
        if response.status_code == 429:
            raise APIError(f"{self.name}: rate limit reached (HTTP 429), try again later.")
        if response.status_code >= 400:
            raise APIError(f"{self.name} returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError:
            raise APIError(f"{self.name} returned a response that is not JSON.") from None

    def _bind(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        declared = {p.name for p in self.params}
        unknown = sorted(set(kwargs) - declared)
        if unknown:
            raise APIError(f"Unknown argument(s) for {self.name}: {', '.join(unknown)}.")

        args: dict[str, Any] = {}
        for param in self.params:
            value = kwargs.get(param.name)
            if value is None or (isinstance(value, str) and not value.strip()):
                if param.required:
                    raise APIError(f"Missing required argument '{param.name}' for {self.name}.")
                args[param.name] = param.default
            else:
                args[param.name] = _coerce(param, value)
        return args

    def function_schema(self) -> dict:
        properties: dict[str, dict] = {}
        for param in self.params:
            prop: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum is not None:
                prop["enum"] = list(param.enum)
            properties[param.name] = prop
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [p.name for p in self.params if p.required],
            },
        }

    def registry_entry(self) -> dict:
        entry = super().registry_entry()
        for param in self.params:
            if not param.required and param.default is not None:
                entry["parameters"][param.name]["default"] = param.default
        return entry
