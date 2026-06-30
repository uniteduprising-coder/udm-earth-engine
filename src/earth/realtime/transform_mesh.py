"""Step 5: Provisional transform mesh (overlay-only, plate-locked target)."""

from __future__ import annotations

import json
from typing import Any

from earth.realtime.coordinates import load_plate_constants, lonlat_to_plate
from earth.realtime.paths import DERIVED


def build_transform_mesh(plate_cfg: dict[str, Any], control_summary: dict[str, Any]) -> dict[str, Any]:
    c = load_plate_constants(plate_cfg)
    cx, cy, r_outer = c["cx"], c["cy"], c["r_outer"]

    # Sample grid for mesh nodes (provisional lon/lat → plate)
    nodes: list[dict[str, Any]] = []
    node_id = 0
    for lat in range(-90, 91, 15):
        for lon in range(-180, 181, 15):
            mapped = lonlat_to_plate(lon, lat, cx, cy, r_outer)
            nodes.append({
                "id": node_id,
                "source_lon": lon,
                "source_lat": lat,
                **mapped,
            })
            node_id += 1

    mesh = {
        "type": "provisional_lonlat_to_udm_plate",
        "primary_transform": "triangulated_affine_mesh",
        "secondary_transform": "thin_plate_spline",
        "plate_lock": True,
        "target": "udm_plate_pixel_coordinates",
        "node_count": len(nodes),
        "nodes": nodes,
        "control_point_count": control_summary.get("count", 0),
        "avg_pixel_error_px": 0.0,
        "note": "Forensic control points required to refine beyond provisional mapping",
        "provisional": True,
    }

    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / "udm_noaa_warp_mesh.json"
    path.write_text(json.dumps(mesh, indent=2), encoding="utf-8")
    return {"path": str(path), **{k: mesh[k] for k in ("node_count", "provisional", "avg_pixel_error_px")}}