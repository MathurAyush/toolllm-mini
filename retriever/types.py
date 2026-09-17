from __future__ import annotations

from dataclasses import dataclass

from apis.base import BaseAPI


@dataclass
class RetrievedAPI:
    api: BaseAPI
    score: float
