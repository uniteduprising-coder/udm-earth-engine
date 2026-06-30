"""Step 4: Control point scaffold — provisional until forensic registration."""

from __future__ import annotations

import csv
from typing import Any

from earth.realtime.coordinates import load_plate_constants, lonlat_to_plate, rho_theta_to_plate
from earth.realtime.paths import DERIVED

COLUMNS = [
    "id", "name", "type", "plate_x", "plate_y", "rho", "theta",
    "source_lon", "source_lat", "confidence", "notes",
]

SEED_POINTS: list[dict[str, Any]] = [
    {"id": 1, "name": "North Axis Aperture", "type": "central_aperture", "rho": 0.0, "theta": 0.0,
     "source_lon": "", "source_lat": "90", "confidence": "high", "notes": "plate center register"},
    {"id": 2, "name": "Equator Bloch Wall N", "type": "equator_crossing", "rho": 0.5, "theta": 0.0,
     "source_lon": "0", "source_lat": "0", "confidence": "medium", "notes": "provisional"},
    {"id": 3, "name": "Equator Bloch Wall E", "type": "equator_crossing", "rho": 0.5, "theta": 1.5708,
     "source_lon": "90", "source_lat": "0", "confidence": "medium", "notes": "provisional"},
    {"id": 4, "name": "Southern Return S", "type": "outer_rim", "rho": 1.0, "theta": 3.14159,
     "source_lon": "180", "source_lat": "-90", "confidence": "low", "notes": "provisional rim"},
    {"id": 5, "name": "Arctic Band", "type": "polar_basin_edge", "rho": 0.13, "theta": 0.0,
     "source_lon": "0", "source_lat": "66.6", "confidence": "low", "notes": "rho band from spec"},
    {"id": 6, "name": "Northern Tropic", "type": "parallel_marker", "rho": 0.37, "theta": 0.0,
     "source_lon": "0", "source_lat": "23.4", "confidence": "low", "notes": "rho band from spec"},
    {"id": 7, "name": "Southern Tropic", "type": "parallel_marker", "rho": 0.63, "theta": 0.0,
     "source_lon": "0", "source_lat": "-23.4", "confidence": "low", "notes": "rho band from spec"},
    {"id": 8, "name": "Outer Antarctic Band", "type": "outer_rim", "rho": 0.87, "theta": 0.0,
     "source_lon": "0", "source_lat": "-66.6", "confidence": "low", "notes": "rho band from spec"},
    {"id": 9, "name": "Greenland-like NE", "type": "greenland_outline", "rho": 0.2, "theta": -0.4,
     "source_lon": "-40", "source_lat": "72", "confidence": "unknown", "notes": "needs visual lock"},
    {"id": 10, "name": "North America-like", "type": "north_america_outline", "rho": 0.35, "theta": -1.2,
     "source_lon": "-100", "source_lat": "45", "confidence": "unknown", "notes": "needs visual lock"},
    {"id": 11, "name": "Africa-like", "type": "africa_outline", "rho": 0.45, "theta": 0.2,
     "source_lon": "20", "source_lat": "5", "confidence": "unknown", "notes": "needs visual lock"},
    {"id": 12, "name": "Pacific Trench Proxy", "type": "ocean_trench", "rho": 0.55, "theta": 2.8,
     "source_lon": "145", "source_lat": "-10", "confidence": "unknown", "notes": "needs bathymetry match"},
]


def build_control_points(plate_cfg: dict[str, Any]) -> dict[str, Any]:
    c = load_plate_constants(plate_cfg)
    cx, cy, r_outer = c["cx"], c["cy"], c["r_outer"]
    rows: list[dict[str, Any]] = []

    for pt in SEED_POINTS:
        rho = float(pt["rho"])
        theta = float(pt["theta"])
        x_px, y_px = rho_theta_to_plate(rho, theta, cx, cy, r_outer)
        if pt.get("source_lon") and pt.get("source_lat"):
            mapped = lonlat_to_plate(float(pt["source_lon"]), float(pt["source_lat"]), cx, cy, r_outer)
        else:
            mapped = {"plate_x": x_px, "plate_y": y_px}
        rows.append({
            **pt,
            "plate_x": round(mapped["plate_x"], 2),
            "plate_y": round(mapped["plate_y"], 2),
            "rho": round(rho, 6),
            "theta": round(theta, 6),
        })

    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / "udm_control_points.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in COLUMNS})

    count = len(rows)
    grade = "crude" if count >= 12 else "insufficient"
    return {
        "path": str(path),
        "count": count,
        "grade": grade,
        "missing_categories": [
            "fourfold_central_island_divisions",
            "mid_ocean_ridge_intersections",
            "vortex_arm_intersections",
            "forensic_bathymetry_locks",
        ],
    }