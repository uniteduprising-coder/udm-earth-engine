from __future__ import annotations

import json
from pathlib import Path

from earth.handlers.base import FeedHandler
from earth.projection.udm import feature_collection


def load_seed(settings, filename: str) -> list[dict]:
    path = settings.seed_path / filename
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sites", data if isinstance(data, list) else [])


class SuppressedEventsHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        sites = load_seed(self.settings, "suppressed_events.json")
        return self.cache(
            feed["id"],
            {
                "layer_id": "suppressed_events",
                "count": len(sites),
                "geojson": feature_collection(sites, layer_id="suppressed_events"),
                "sites": sites,
            },
        )


class MasonicTemplesHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        sites = load_seed(self.settings, "masonic_temples.json")
        return self.cache(
            feed["id"],
            {
                "layer_id": "masonic_temples",
                "count": len(sites),
                "geojson": feature_collection(sites, layer_id="masonic_temples"),
                "sites": sites,
            },
        )


def seed_layer_geojson(settings, layer_id: str, filename: str) -> dict:
    sites = load_seed(settings, filename)
    for s in sites:
        s["layer_id"] = layer_id
    return feature_collection(sites, layer_id=layer_id)