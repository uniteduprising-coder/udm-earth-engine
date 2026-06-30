"""Step 2–3: Feature edges and polar unwrap (plate-dependent)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from earth.realtime.coordinates import load_plate_constants
from earth.realtime.paths import DERIVED, PLATES


def extract_feature_edges(plate_cfg: dict[str, Any]) -> dict[str, Any]:
    disk = plate_cfg["full_disk_plate"]
    path = PLATES / disk["file"]
    geojson = {
        "type": "FeatureCollection",
        "features": [],
        "metadata": {
            "status": "scaffold",
            "note": "Edge detection requires master plate + Pillow/OpenCV pass",
        },
    }
    if path.exists():
        geojson["metadata"]["status"] = "pending_extraction"
        geojson["metadata"]["plate"] = disk["file"]
    else:
        geojson["metadata"]["status"] = "needs_manual_review"

    DERIVED.mkdir(parents=True, exist_ok=True)
    out = DERIVED / "udm_feature_edges.geojson"
    out.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    return {"path": str(out), "feature_count": 0, "status": geojson["metadata"]["status"]}


def build_unwrapped_plate(plate_cfg: dict[str, Any], disk_solution: dict[str, Any]) -> dict[str, Any]:
    disk = plate_cfg["full_disk_plate"]
    path = PLATES / disk["file"]
    out = DERIVED / "udm_unwrapped_plate.png"
    if not path.exists():
        return {"path": str(out), "status": "needs_manual_review", "written": False}

    try:
        from PIL import Image
        import math

        c = load_plate_constants(plate_cfg)
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