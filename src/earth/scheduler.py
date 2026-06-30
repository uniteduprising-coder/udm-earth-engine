"""Background polling scheduler."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from earth.config import get_settings
from earth.handlers.registry import HandlerRegistry


class FeedScheduler:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.registry = HandlerRegistry(self.settings)
        self.scheduler = AsyncIOScheduler()

    async def _run_feed(self, feed: dict) -> None:
        if not feed.get("enabled"):
            return
        handler = self.registry.get(feed["handler"])
        await handler.fetch(feed)

    async def refresh_all(self) -> list[str]:
        refreshed = []
        for feed in self.settings.load_feeds():
            if feed.get("enabled"):
                await self._run_feed(feed)
                refreshed.append(feed["id"])
        for layer in self.settings.load_layers():
            handler_name = layer.get("handler")
            if handler_name in ("suppressed_events", "masonic_temples", "forensic_bridge"):
                handler = self.registry.get(handler_name)
                await handler.fetch({"id": layer["id"], "enabled": True})
                refreshed.append(layer["id"])
        return refreshed

    def start(self) -> None:
        for feed in self.settings.load_feeds():
            if feed.get("type") != "poll" or not feed.get("enabled"):
                continue
            interval = feed.get("interval_seconds", 300)
            self.scheduler.add_job(
                self._run_feed,
                "interval",
                seconds=interval,
                args=[feed],
                id=feed["id"],
                replace_existing=True,
            )
        self.scheduler.start()