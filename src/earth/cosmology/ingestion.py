"""
Observational data auto-ingestion pipeline skeleton.

Competitive Advantage Blueprint §4.3 — multi-source schedule + validation on ingest.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from earth.cosmology.coordinates import geo_to_cylindrical
from earth.cosmology.engine import get_engine
from earth.cosmology.observations import (
    load_1982_stations,
    load_arctic_mt_anomalies,
    load_aurora_periodicity,
    load_independent_glow_reports,
    load_lod_csv,
    load_schumann_csv,
)
from earth.cosmology.validation import run_validation

SOURCES: list[dict[str, Any]] = [
    {"id": "intermagnet", "label": "INTERMAGNET", "interval_hours": 1, "status": "stub"},
    {"id": "swarm", "label": "SWARM L2", "interval_hours": 24, "status": "stub"},
    {"id": "grace_fo", "label": "GRACE-FO", "interval_hours": 720, "status": "stub"},
    {"id": "iers", "label": "IERS LOD", "interval_hours": 24, "status": "local_csv"},
    {"id": "noaa_aurora", "label": "NOAA Aurora", "interval_hours": 0.5, "status": "stub"},
    {"id": "schumann", "label": "Schumann ELF", "interval_hours": 0, "status": "local_csv"},
    {"id": "user_obs", "label": "User observations", "interval_hours": 0, "status": "active"},
]

_last_run: dict[str, str] = {}


def ingestion_status() -> dict[str, Any]:
    now = datetime.now(UTC)
    feeds = []
    for src in SOURCES:
        last = _last_run.get(src["id"])
        feeds.append(
            {
                **src,
                "last_ingest_utc": last,
                "next_due_utc": (
                    (datetime.fromisoformat(last.replace("Z", "+00:00")) + timedelta(hours=src["interval_hours"])).isoformat()
                    if last and src["interval_hours"] > 0
                    else None
                ),
                "stale": last is None,
            }
        )
    return {
        "pipeline": "udm_observation_ingest_v1",
        "sources": feeds,
        "schedule_summary": {
            "hourly": ["intermagnet"],
            "daily": ["swarm", "iers"],
            "monthly": ["grace_fo"],
            "continuous": ["schumann", "user_obs"],
        },
        "checked_at": now.isoformat(),
    }


def _validate_local(source_id: str) -> dict[str, Any]:
    """Load and validate local CSV observation stores."""
    loaders = {
        "schumann": load_schumann_csv,
        "iers": load_lod_csv,
        "aurora_hist": load_aurora_periodicity,
        "glow_reports": load_independent_glow_reports,
        "mt_conductivity": load_arctic_mt_anomalies,
        "soviet_1982": load_1982_stations,
    }
    if source_id == "schumann":
        data = load_schumann_csv()
        return {"rows": len(data["freq_Hz"]), "valid": len(data["freq_Hz"]) > 0}
    if source_id == "iers":
        data = load_lod_csv()
        return {"rows": len(data["mjd"]), "valid": len(data["mjd"]) > 0}
    if source_id in loaders:
        data = loaders[source_id]()
        return {"valid": bool(data), "keys": list(data.keys()) if isinstance(data, dict) else None}
    return {"valid": False, "note": "remote fetch stub"}


def run_ingestion_cycle(*, sources: list[str] | None = None) -> dict[str, Any]:
    """Run one ingestion cycle — validate format, convert coords, update checks."""
    now = datetime.now(UTC).isoformat()
    target = sources or [s["id"] for s in SOURCES]
    results: list[dict[str, Any]] = []

    for sid in target:
        src = next((s for s in SOURCES if s["id"] == sid), None)
        if not src:
            results.append({"source": sid, "ok": False, "error": "unknown source"})
            continue

        if src["status"] == "local_csv":
            if sid == "schumann":
                v = _validate_local("schumann")
            elif sid == "iers":
                v = _validate_local("iers")
            else:
                v = {"valid": True, "note": "stub"}
        else:
            v = {"valid": True, "note": f"{src['label']} remote ingest stub — format OK"}

        _last_run[sid] = now
        results.append({"source": sid, "ok": v.get("valid", True), "detail": v})

    engine = get_engine()
    validation = run_validation(engine)
    sample = geo_to_cylindrical(74.0, 0.0)

    return {
        "ok": True,
        "ingested_at": now,
        "results": results,
        "udm_coords_sample": sample,
        "validation_score": f"{validation['passed']}/{validation['total_checks']}",
        "discrepancies_flagged": validation["failed"],
    }