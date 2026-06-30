"""Publish realtime renders to public/ for web viewer."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from earth.config import ROOT
from earth.realtime.paths import DERIVED, MODEL_ROOT, RENDERS

PUBLIC_RT = ROOT / "public" / "data" / "realtime"


def publish_to_public(disk: dict, report: dict) -> dict[str, str]:
    PUBLIC_RT.mkdir(parents=True, exist_ok=True)
    published: dict[str, str] = {}

    copies = [
        (RENDERS / "udm_composite.png", "composite.png"),
        (RENDERS / "udm_live_geocolor.png", "geocolor.png"),
        (RENDERS / "udm_base_plate_ref.jpg", "base_plate.jpg"),
        (DERIVED / "udm_unwrapped_plate.png", "unwrapped.png"),
        (MODEL_ROOT / "plates" / "1000083849.jpg", "central_zoom.jpg"),
        (DERIVED / "udm_disk_solution.json", "disk.json"),
        (RENDERS / "udm_live_spaceweather.json", "spaceweather.json"),
        (MODEL_ROOT / "logs" / "latest_run_report.json", "report.json"),
    ]
    for src, name in copies:
        if src.exists():
            dst = PUBLIC_RT / name
            shutil.copy2(src, dst)
            published[name] = f"/data/realtime/{name}"

    manifest = {
        "plate_lock": True,
        "viewer": "/realtime",
        "assets": published,
        "disk": disk,
        "report_summary": {
            "control_grade": report.get("derived", {}).get("control_grade"),
            "validation": report.get("validation"),
            "needs_manual_review": report.get("needs_manual_review", []),
        },
    }
    (PUBLIC_RT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    published["manifest"] = "/data/realtime/manifest.json"
    return published