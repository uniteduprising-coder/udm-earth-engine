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

    # Sample radial brightness falloff at initial center to estimate rim
    pixels = img.load()
    samples: list[tuple[float, float]] = []
    for deg in range(0, 360, 6):
        rad = math.radians(deg)
        for frac in (0.85, 0.9, 0.95, 1.0):
            r = r0 * frac
            x = int(cx0 + r * math.sin(rad))
            y = int(cy0 - r * math.cos(rad))
            if 0 <= x < w and 0 <= y < h:
                samples.append((frac, float(pixels[x, y])))

    rim_brightness = sum(v for _, v in samples) / max(len(samples), 1)
    refined = {
        "center_px_initial": initial["center_px_initial"],
        "center_px_refined": [cx0, cy0],
        "outer_radius_px_initial": r0,
        "outer_radius_px_refined": r0,
        "refinement_reason": "pillow_available_no_shift_detected_yet",
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