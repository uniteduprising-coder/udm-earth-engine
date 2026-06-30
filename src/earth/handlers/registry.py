from __future__ import annotations

from earth.config import Settings
from earth.handlers.ephemeris import EphemerisHandler
from earth.handlers.forensic_bridge import ForensicBridgeHandler
from earth.handlers.geo_stream_bridge import GeoStreamBridgeHandler
from earth.handlers.nasa_epic import NasaEpicHandler
from earth.handlers.seed_layers import MasonicTemplesHandler, SuppressedEventsHandler
from earth.handlers.sites_kml import SitesLayersHandler
from earth.handlers.udm_grid import UdmGridHandler


class HandlerRegistry:
    def __init__(self, settings: Settings) -> None:
        self._map = {
            "nasa_epic": NasaEpicHandler(settings),
            "ephemeris": EphemerisHandler(settings),
            "geo_stream_bridge": GeoStreamBridgeHandler(settings),
            "sites_layers": SitesLayersHandler(settings),
            "udm_grid": UdmGridHandler(settings),
            "suppressed_events": SuppressedEventsHandler(settings),
            "masonic_temples": MasonicTemplesHandler(settings),
            "forensic_bridge": ForensicBridgeHandler(settings),
        }

    def get(self, name: str):
        if name not in self._map:
            raise ValueError(f"Unknown handler: {name}")
        return self._map[name]