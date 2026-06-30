"""UDM Real-Time Earth Model API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from earth.realtime.paths import DERIVED, LOGS, MODEL_ROOT, RENDERS
from earth.realtime.pipeline import run_realtime_pipeline

router = APIRouter(tags=["realtime"])


def _read_json(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@router.get("/realtime/status")
async def realtime_status():
    return {
        "model": "UDM Real-Time Earth Model",
        "root": str(MODEL_ROOT),
        "plate_lock": True,
        "report": _read_json(LOGS / "latest_run_report.json"),
        "source_status": _read_json(LOGS / "source_status.json"),
    }


@router.get("/realtime/disk")
async def realtime_disk():
    return _read_json(DERIVED / "udm_disk_solution.json") or {"error": "run pipeline first"}


@router.get("/realtime/mesh")
async def realtime_mesh():
    return _read_json(DERIVED / "udm_noaa_warp_mesh.json") or {"error": "run pipeline first"}


@router.get("/realtime/spaceweather")
async def realtime_spaceweather():
    return _read_json(RENDERS / "udm_live_spaceweather.json") or {"error": "run pipeline first"}


@router.post("/realtime/run")
async def realtime_run():
    return await run_realtime_pipeline()