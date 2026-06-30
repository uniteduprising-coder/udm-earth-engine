"""Step 6: Render composite layers (overlays only — never overwrite master plate)."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from earth.realtime.paths import PLATES, RENDERS


def render_outputs(
    plate_cfg: dict[str, Any],
    swpc: dict[str, Any],
    disk: dict[str, Any],
    warp_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    RENDERS.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Any] = {"rendered_at": datetime.now(UTC).isoformat(), "files": {}}

    # Spaceweather summary (always)
    sw_path = RENDERS / "udm_live_spaceweather.json"
    sw_path.write_text(json.dumps(swpc, indent=2), encoding="utf-8")
    outputs["files"]["spaceweather"] = str(sw_path)

    # Base plate copy (read-only reference in renders — original in plates/ untouched)
    disk_file = plate_cfg["full_disk_plate"]["file"]
    src = PLATES / disk_file
    if src.exists():
        dst = RENDERS / "udm_base_plate_ref.jpg"
        shutil.copy2(src, dst)
        outputs["files"]["base_plate_ref"] = str(dst)
    else:
        outputs["files"]["base_plate_ref"] = None
        outputs["plate_missing"] = True

    geocolor_status = "pending"
    if warp_result and warp_result.get("layers", {}).get("geocolor", {}).get("ok"):
        geocolor_status = "ok"
        outputs["files"]["geocolor"] = str(RENDERS / "udm_live_geocolor.png")
    if (RENDERS / "udm_composite.png").exists():
        outputs["files"]["composite_png"] = str(RENDERS / "udm_composite.png")

    composite = {
        "plate_lock": True,
        "base": disk_file if src.exists() else None,
        "overlays": {
            "geocolor": {"status": geocolor_status, "source": "nasa_gibs_viirs"},
            "infrared": {"status": "pending"},
            "water_vapor": {"status": "pending"},
        },
        "field": swpc.get("files", {}),
        "disk": {k: disk.get(k) for k in ("center_px_initial", "outer_radius_px_initial", "plate_present")},
        "warp": warp_result,
    }
    comp_path = RENDERS / "udm_composite.json"
    comp_path.write_text(json.dumps(composite, indent=2), encoding="utf-8")
    outputs["files"]["composite_manifest"] = str(comp_path)

    return outputs