from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from earth.config import Settings


class FeedHandler(ABC):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def fetch(self, feed: dict) -> dict:
        ...

    def cache(self, feed_id: str, payload: dict) -> dict:
        record = {
            "feed_id": feed_id,
            "fetched_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        path = self.settings.cache_path / f"{feed_id}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def read_cache(self, feed_id: str) -> dict | None:
        path = self.settings.cache_path / f"{feed_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))