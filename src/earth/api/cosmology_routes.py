from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from earth.cosmology.chromatic import (
    day_night_state,
    full_chromatic_synthesis,
    solar_geometry,
    terminator_profile,
)
from earth.cosmology.coordinates import geo_to_cylindrical, project_site
from earth.cosmology.engine import get_engine, reset_engine
from earth.cosmology.observations import list_observation_layers, load_1982_stations
from earth.cosmology.params import (
    export_params_json,
    load_luminary_spectra,
    load_node_table,
    load_params,
    save_params,
)
from earth.cosmology.validation import run_validation, validate_1982_glow

router = APIRouter(tags=["cosmology"])


@router.get("/params")
async def get_params():
    return {
        "source": "params.yml",
        "status": "all_constants_defined",
        "blocking_gaps": 0,
        "version": "5.2α",
        "params": load_params(),
        "nodes": load_node_table(),
        "time": datetime.now(UTC).isoformat(),
    }


@router.post("/update")
async def update_params(
    key: str | None = Query(None),
    val: float | None = Query(None),
    body: dict[str, Any] | None = Body(None),
):
    """Rewrite params.yml and restart micro-loop (§0)."""
    updates: dict[str, Any] = {}
    if key is not None and val is not None:
        updates[key] = val
    if body:
        updates.update(body)
    if not updates:
        raise HTTPException(400, "Provide key/val query or JSON body")
    params = save_params(updates)
    engine = get_engine()
    engine.reload_params(params)
    return {"ok": True, "updated": list(updates.keys()), "params": params, "restarted": True}


@router.get("/cosmology/state")
async def cosmology_state():
    return get_engine().state()


@router.post("/cosmology/step")
async def cosmology_step(steps: int = Query(1, ge=1, le=100)):
    engine = get_engine()
    records = [engine.macro_step_tick() for _ in range(steps)]
    return {"ok": True, "steps": steps, "records": records, "state": engine.state()}


@router.get("/cosmology/field")
async def cosmology_field(
    r_mi: float = Query(..., gt=0),
    theta_rad: float = Query(0.0),
    z_mi: float = Query(0.0, ge=0),
    t_s: float | None = Query(None),
):
    return get_engine().field_sample(r_mi, theta_rad, z_mi=z_mi, t_s=t_s)


@router.get("/cosmology/project")
async def cosmology_project(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    mode: str = Query("udm_v5"),
):
    return project_site(lat, lon, mode=mode)


@router.get("/cosmology/cylindrical")
async def cosmology_cylindrical(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    return geo_to_cylindrical(lat, lon)


@router.get("/validate")
async def validate():
    return run_validation(get_engine())


@router.post("/run_full_validation")
async def run_full_validation():
    engine = get_engine()
    for _ in range(5):
        engine.macro_step_tick()
    report = run_validation(engine)
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["glow_anchor"] = validate_1982_glow(engine)
    return report


@router.get("/observations/layers")
async def observation_layers():
    return {"layers": list_observation_layers()}


@router.get("/observations/soviet_1982")
async def soviet_1982():
    return load_1982_stations()


@router.get("/cosmology/spectra")
async def luminary_spectra():
    return {"lines": load_luminary_spectra(), "nodes": ["Sun", "Moon"]}


@router.get("/cosmology/chromatic")
async def cosmology_chromatic(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    r_mi: float | None = Query(None, ge=0),
    theta_rad: float | None = Query(None),
    t_s: float = Query(0.0, ge=0),
):
    """Day/night, terminator, and chromatic synthesis (v5.2α)."""
    if lat is not None and lon is not None:
        return full_chromatic_synthesis(lat=lat, lon=lon, t_s=t_s)
    return full_chromatic_synthesis(
        r_mi=r_mi or 70.0,
        theta_rad=theta_rad if theta_rad is not None else 0.785,
        t_s=t_s,
    )


@router.get("/cosmology/daynight")
async def cosmology_daynight(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    t_s: float = Query(0.0, ge=0),
):
    cyl = geo_to_cylindrical(lat, lon)
    return day_night_state(cyl["r_mi"], cyl["theta_rad"], t_s=t_s)


@router.get("/cosmology/terminator")
async def cosmology_terminator(t_s: float = Query(0.0, ge=0)):
    return {
        "solar": solar_geometry(),
        "terminator": terminator_profile(t_s=t_s),
    }


@router.post("/cosmology/reset")
async def cosmology_reset():
    engine = reset_engine()
    return {"ok": True, "state": engine.state()}


@router.post("/export_session")
async def export_session():
    engine = get_engine()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "state": engine.state(),
        "validation": run_validation(engine),
        "telemetry_tail": engine.telemetry[-20:],
    }


def bake_public_assets() -> None:
    """Export params.json for edge CDN."""
    export_params_json()