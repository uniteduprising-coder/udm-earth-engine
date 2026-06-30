"""UDM Real-Time Earth Model — full run pipeline."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from earth.realtime.control_points import build_control_points
from earth.realtime.disk_solver import solve_disk
from earth.realtime.features import build_unwrapped_plate, extract_feature_edges
from earth.realtime.grid import build_grid_geojson
from earth.realtime.paths import CONFIG, DERIVED, LOGS, MODEL_ROOT, ensure_dirs
from earth.realtime.render import render_outputs
from earth.realtime.sources import check_all_sources, pull_gfz_kp, pull_swpc
from earth.realtime.transform_mesh import build_transform_mesh
from earth.realtime.validation import run_validation


def load_plate_config() -> dict[str, Any]:
    with (CONFIG / "udm_master_plate.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _log_ingest(entry: dict[str, Any]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS / "ingest_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


async def run_realtime_pipeline() -> dict[str, Any]:
    """Execute RUN COMMAND GOAL from root prompt."""
    ensure_dirs()
    plate_cfg = load_plate_config()
    started = datetime.now(UTC).isoformat()

    disk = solve_disk(plate_cfg)
    grid_paths = build_grid_geojson(plate_cfg)
    features = extract_feature_edges(plate_cfg)
    unwrap = build_unwrapped_plate(plate_cfg, disk)
    control = build_control_points(plate_cfg)
    mesh = build_transform_mesh(plate_cfg, control)

    source_status = await check_all_sources()
    swpc = await pull_swpc()
    gfz = await pull_gfz_kp()

    validation = run_validation(disk, control, mesh, source_status)
    renders = render_outputs(plate_cfg, swpc, disk)

    report = {
        "ok": True,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "model_root": str(MODEL_ROOT),
        "plate_lock_preserved": validation["plate_lock_preserved"],
        "plates_present": {
            "full_disk": (MODEL_ROOT / "plates" / plate_cfg["full_disk_plate"]["file"]).exists(),
            "central_zoom": (MODEL_ROOT / "plates" / plate_cfg["central_zoom_plate"]["file"]).exists(),
        },
        "derived": {
            "disk_solution": str(DERIVED / "udm_disk_solution.json"),
            "control_points": control["path"],
            "control_grade": control["grade"],
            "mesh_nodes": mesh["node_count"],
            **grid_paths,
            "feature_edges": features["path"],
            "unwrapped": unwrap,
        },
        "pulls": {
            "swpc": swpc,
            "gfz_kp": gfz,
        },
        "source_status_summary": {
            name: s.get("status") if isinstance(s, dict) else s
            for name, s in source_status.get("sources", {}).items()
        },
        "validation": validation,
        "renders": renders,
        "needs_manual_review": [
            item for item in [
                "master_plates_missing" if not disk.get("plate_present") else None,
                "central_zoom_plate_missing" if not (MODEL_ROOT / "plates" / plate_cfg["central_zoom_plate"]["file"]).exists() else None,
                "feature_extraction_pending" if features["status"] != "ok" else None,
                "atmospheric_warp_pending" if renders.get("plate_missing") else None,
                *control.get("missing_categories", []),
            ]
            if item
        ],
        "failed": [
            k for k, v in swpc.get("files", {}).items()
            if isinstance(v, dict) and not v.get("ok")
        ],
        "stale": [
            k for k, v in source_status.get("sources", {}).items()
            if isinstance(v, dict) and v.get("status") in ("stale", "offline", "blocked")
        ],
    }

    report_path = LOGS / "latest_run_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _log_ingest({"event": "pipeline_complete", "report": str(report_path), "ok": report["ok"]})
    return report


def run_realtime_pipeline_sync() -> dict[str, Any]:
    return asyncio.run(run_realtime_pipeline())