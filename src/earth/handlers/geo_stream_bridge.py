from __future__ import annotations

import httpx

from earth.handlers.base import FeedHandler

BRIDGE_FEEDS = ["schumann_resonance", "nasa_donki_flares", "weather_local"]


class GeoStreamBridgeHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        base = self.settings.geo_stream_local if self.settings.app_env == "development" else self.settings.geo_stream_base
        merged: dict = {"source": base, "feeds": {}}
        async with httpx.AsyncClient(timeout=30) as client:
            for fid in BRIDGE_FEEDS:
                try:
                    resp = await client.get(f"{base}/v1/stream/{fid}")
                    if resp.status_code == 200:
                        merged["feeds"][fid] = resp.json()
                    else:
                        merged["feeds"][fid] = {"error": resp.status_code}
                except Exception as exc:
                    merged["feeds"][fid] = {"error": str(exc)}
        return self.cache(feed["id"], merged)