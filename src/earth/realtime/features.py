"""Step 2–3: Feature edges and polar unwrap."""

from __future__ import annotations

import json
import math
from typing import Any

from earth.realtime.coordinates import load_plate_constants
from earth.realtime.paths import DERIVED, PLATES


def extract_feature_edges(plate_cfg: dict[str, Any], disk: dict[str, Any] | None = None) -> dict[str, Any]:
    disk = disk or {}
    disk_file = plate_cfg["full_disk_plate"]
    path = PLATES / disk_file["file"]

    geojson: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": [],
        "metadata": {"status": "needs_manual_review", "plate": disk_file["file"]},
    }

    if not path.exists():
        DERIVED.mkdir(parents=True, exist_ok=True)
        out = DERIVED / "udm_feature_edges.geojson"
        out.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
        return {"path": str(out), "feature_count": 0, "status": "needs_manual_review"}

    try:
        from PIL import Image, ImageFilter

        c = load_plate_constants(plate_cfg)
        if disk.get("center_px_refined"):
            c["cx"] = float(disk["center_px_refined"][0])
            c["cy"] = float(disk["center_px_refined"][1])
            c["r_outer"] = float(disk.get("outer_radius_px_refined", c["r_outer"]))

        img = Image.open(path).convert("L")
        edges = img.filter(ImageFilter.FIND_EDGES)
        ep = edges.load()
        w, h = edges.size
        cx, cy, r_outer = c["cx"], c["cy"], c["r_outer"]

        # Sample edge points within disk (stride for performance)
        coords: list[list[float]] = []
        stride = 6
        for y in range(0, h, stride):
            for x in range(0, w, stride):
                dx, dy = x - cx, cy - y
                if math.hypot(dx, dy) > r_outer:
                    continue
                if ep[x, y] > 40:
                    coords.append([float(x), float(y)])

        # Downsample to max 2000 points for GeoJSON size
        if len(coords) > 2000:
            step = len(coords) // 2000
            coords = coords[::step]

        if coords:
            geojson["features"].append({
                "type": "Feature",
                "properties": {"type": "bathymetric_edge_sample", "count": len(coords)},
                "geometry": {"type": "MultiPoint", "coordinates": coords},
            })

        geojson["metadata"] = {
            "status": "ok",
            "plate": disk_file["file"],
            "edge_points": len(coords),
            "method": "pillow_find_edges",
        }
    except ImportError:
        geojson["metadata"]["status"] = "pillow_required"

    DERIVED.mkdir(parents=True, exist_ok=True)
    out = DERIVED / "udm_feature_edges.geojson"
    out.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    return {
        "path": str(out),
        "feature_count": len(geojson["features"]),
        "status": geojson["metadata"]["status"],
        "edge_points": geojson["metadata"].get("edge_points", 0),
    }


def build_unwrapped_plate(plate_cfg: dict[str, Any], disk_solution: dict[str, Any]) -> dict[str, Any]:
    disk = plate_cfg["full_disk_plate"]
    path = PLATES / disk["file"]
    out = DERIVED / "udm_unwrapped_plate.png"
    if not path.exists():
        return {"path": str(out), "status": "needs_manual_review", "written": False}

    try:
        from PIL import Image

        c = load_plate_constants(plate_cfg)
        if disk_solution.get("center_px_refined"):
            c["cx"] = float(disk_solution["center_px_refined"][0])
            c["cy"] = float(disk_solution["center_px_refined"][1])
            c["r_outer"] = float(disk_solution.get("outer_radius_px_refined", c["r_outer"]))

        img = Image.open(path).convert("RGB")
        w_out, h_out = 720, 360
        unwrapped = Image.new("RGB", (w_out, h_out))
        src = img.load()
        dst = unwrapped.load()
        iw, ih = img.size
        cx, cy, r_outer = c["cx"], c["cy"], c["r_outer"]

        for j in range(h_out):
            rho = j / (h_out - 1)
            r = rho * r_outer
            for i in range(w_out):
                theta = (i / (w_out - 1)) * 2 * math.pi - math.pi
                x = int(cx + r * math.sin(theta))
                y = int(cy - r * math.cos(theta))
                if 0 <= x < iw and 0 <= y < ih:
                    dst[i, j] = src[x, y]
        unwrapped.save(out)
        return {"path": str(out), "status": "ok", "written": True, "size": [w_out, h_out]}
    except ImportError:
        return {"path": str(out), "status": "pillow_required", "written": False}