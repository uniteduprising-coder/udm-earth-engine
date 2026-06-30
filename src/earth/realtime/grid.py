"""Meridians, parallels, equator ring — fitted to UDM plate coordinates."""

from __future__ import annotations

import json
import math
from typing import Any

from earth.realtime.coordinates import load_plate_constants, rho_from_phi_udm, rho_theta_to_plate
from earth.realtime.paths import DERIVED


def _ring_polygon(cx: float, cy: float, r_outer: float, rho: float, segments: int = 360) -> list[list[float]]:
    r = rho * r_outer
    coords: list[list[float]] = []
    for i in range(segments + 1):
        theta = 2 * math.pi * i / segments
        x, y = rho_theta_to_plate(rho, theta, cx, cy, r_outer)
        coords.append([round(x, 2), round(y, 2)])
    return coords


def _meridian_line(cx: float, cy: float, r_outer: float, theta_deg: float) -> list[list[float]]:
    theta = math.radians(theta_deg)
    coords: list[list[float]] = []
    for rho in [i / 200 for i in range(201)]:
        x, y = rho_theta_to_plate(rho, theta, cx, cy, r_outer)
        coords.append([round(x, 2), round(y, 2)])
    return coords


def build_grid_geojson(plate_cfg: dict[str, Any]) -> dict[str, str]:
    c = load_plate_constants(plate_cfg)
    cx, cy, r_outer = c["cx"], c["cy"], c["r_outer"]

    meridians = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"theta_deg": deg, "major": deg % 15 == 0},
                "geometry": {"type": "LineString", "coordinates": _meridian_line(cx, cy, r_outer, deg)},
            }
            for deg in range(-180, 180, 15)
        ],
    }

    parallels = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"phi_udm_deg": phi, "rho": round(rho_from_phi_udm(phi), 4)},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_ring_polygon(cx, cy, r_outer, rho_from_phi_udm(phi), 180)],
                },
            }
            for phi in range(-90, 91, 5)
        ],
    }

    equator = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"rho": 0.5, "type": "annular_bloch_wall_candidate"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_ring_polygon(cx, cy, r_outer, 0.5, 360)],
                },
            }
        ],
    }

    DERIVED.mkdir(parents=True, exist_ok=True)
    paths = {
        "meridians": DERIVED / "udm_meridians.geojson",
        "parallels": DERIVED / "udm_parallels.geojson",
        "equator": DERIVED / "udm_equator_ring.geojson",
    }
    for key, path in paths.items():
        data = {"meridians": meridians, "parallels": parallels, "equator": equator}[key]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {k: str(v) for k, v in paths.items()}