from __future__ import annotations

from earth.handlers.base import FeedHandler
from earth.projection.udm import (
    ALPHA_ANTI_H,
    KAPPA_COUPLING,
    PHI_NODE_DEG,
    PHI_WIND_DEG,
    amplitude_loading,
    project_flat,
    winding_function,
)


class UdmGridHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        lat_steps = feed.get("lat_steps", 37)
        lon_steps = feed.get("lon_steps", 73)
        lst_hours = feed.get("lst_hours", 12.0)
        cells = []
        for i in range(lat_steps):
            lat = -90 + (180 * i / (lat_steps - 1))
            for j in range(lon_steps):
                lon = -180 + (360 * j / (lon_steps - 1))
                proj = project_flat(lat, lon, lst_hours=lst_hours)
                cells.append(
                    {
                        "lat": round(lat, 2),
                        "lon": round(lon, 2),
                        "W": proj["W"],
                        "x_km": proj["x_km"],
                        "y_km": proj["y_km"],
                        "lat_udm": proj["lat_udm"],
                        "lon_udm": proj["lon_udm"],
                    }
                )
        sample_lats = list(range(-90, 91, 5))
        curve = [
            {
                "lat": lat,
                "W": round(winding_function(lat), 6),
                "A_mmhg": round(amplitude_loading(lat), 6),
            }
            for lat in sample_lats
        ]
        return self.cache(
            feed["id"],
            {
                "constants": {
                    "PHI_WIND_DEG": PHI_WIND_DEG,
                    "PHI_NODE_DEG": PHI_NODE_DEG,
                    "ALPHA_ANTI_H": ALPHA_ANTI_H,
                    "KAPPA_COUPLING": KAPPA_COUPLING,
                },
                "lst_hours": lst_hours,
                "grid": {"lat_steps": lat_steps, "lon_steps": lon_steps, "cells": cells},
                "winding_curve": curve,
            },
        )