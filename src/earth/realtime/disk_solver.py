"""Step 1: Detect disk geometry from master plate (additive refinement only)."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from earth.realtime.coordinates import load_plate_constants
from earth.realtime.paths import DERIVED, PLATES


def _try_pillow_disk(path: Path, initial: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    img = Image.open(path).convert("L")
    w, h = img.size
    cx0, cy0 = initial["center_px_initial"]
    r0 = initial["outer_radius_px_initial"]
    pixels = img.load()

    # Fast centroid of non-black pixels (sample every 4px)
    xs: list[float] = []
    ys: list[float] = []
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            if pixels[x, y] > 25:
                xs.append(x)
                ys.append(y)
    if xs:
        cx_r = sum(xs) / len(xs)
        cy_r = sum(ys) / len(ys)
        rs = sorted(math.hypot(x - cx_r, y - cy_r) for x, y in zip(xs, ys))
        r_r = rs[int(len(rs) * 0.98)] if rs else r0
    else:
        cx_r, cy_r, r_r = cx0, cy0, r0

    samples: list[tuple[float, float]] = []
    for deg in range(0, 360, 12):
        rad = math.radians(deg)
        for frac in (0.9, 0.95, 1.0):
            r = r_r * frac
            x = int(cx_r + r * math.sin(rad))
            y = int(cy_r - r * math.cos(rad))
            if 0 <= x < w and 0 <= y < h:
                samples.append((frac, float(pixels[x, y])))

    rim_brightness = sum(v for _, v in samples) / max(len(samples), 1)
    shift = math.hypot(cx_r - cx0, cy_r - cy0)
    refined = {
        "center_px_initial": initial["center_px_initial"],
        "center_px_refined": [round(cx_r, 1), round(cy_r, 1)],
        "outer_radius_px_initial": r0,
        "outer_radius_px_refined": round(r_r, 1),
        "refinement_reason": "centroid_and_r98_from_plate" if shift < 5 else "centroid_shift_detected",
        "center_shift_px": round(shift, 2),
        "rim_mean_brightness": round(rim_brightness, 2),
        "image_size": [w, h],
    }
    return refined


def solve_disk(plate_cfg: dict[str, Any]) -> dict[str, Any]:
    disk = plate_cfg["full_disk_plate"]
    path = PLATES / disk["file"]
    constants = load_plate_constants(plate_cfg)

    solution: dict[str, Any] = {
        "solved_at": datetime.now(UTC).isoformat(),
        "plate_lock": True,
        "plate_file": disk["file"],
        "plate_present": path.exists(),
        "center_px_initial": disk["center_px_initial"],
        "outer_radius_px_initial": disk["outer_radius_px_initial"],
        "center_px_refined": disk["center_px_initial"],
        "outer_radius_px_refined": disk["outer_radius_px_initial"],
        "refinement_reason": "using_yaml_initial_constants",
        "rim_thickness_px_estimate": None,
        "edge_falloff": None,
        **constants,
    }

    if path.exists():
        refined = _try_pillow_disk(path, disk)
        if refined:
            solution.update(refined)
        else:
            solution["refinement_reason"] = "plate_present_pillow_unavailable_use_initial"
    else:
        solution["status"] = "needs_manual_review"
        solution["note"] = f"Place {disk['file']} in UDM_REALTIME_MODEL/plates/"

    DERIVED.mkdir(parents=True, exist_ok=True)
    out = DERIVED / "udm_disk_solution.json"
    out.write_text(json.dumps(solution, indent=2), encoding="utf-8")
    return solution