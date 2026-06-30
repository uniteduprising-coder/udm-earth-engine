from __future__ import annotations

from datetime import UTC, datetime

import httpx

from earth.handlers.base import FeedHandler


class NasaEpicHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        params = {}
        if self.settings.nasa_api_key:
            params["api_key"] = self.settings.nasa_api_key
        url = f"{self.settings.nasa_epic_base}/natural/latest"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                images = resp.json()
            if isinstance(images, list) and images:
                latest = images[0]
                date = latest.get("date", "")
                image_name = latest.get("image", "")
                epic_url = (
                    f"https://epic.gsfc.nasa.gov/archive/natural/{date.replace('-', '/')}/png/{image_name}.png"
                    if date and image_name
                    else ""
                )
                payload = {
                    "latest": latest,
                    "image_url": epic_url,
                    "caption": "NASA EPIC natural color — full Earth disc",
                }
            else:
                payload = {"images": images, "stub": True}
        except Exception as exc:
            payload = {
                "error": str(exc),
                "stub": True,
                "fallback_url": "https://epic.gsfc.nasa.gov/",
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        return self.cache(feed["id"], payload)