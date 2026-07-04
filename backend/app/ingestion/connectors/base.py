from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

SourceType = Literal["app_store", "play_store", "reddit"]


@dataclass
class RawReview:
    native_id: str
    source: SourceType
    text: str
    title: str | None
    rating: int | None
    author: str
    created_at: datetime
    url: str
    app_name: str
    locale: str | None = None


class ReviewConnector(Protocol):
    def fetch(self, count: int | None = None) -> list[RawReview]: ...
