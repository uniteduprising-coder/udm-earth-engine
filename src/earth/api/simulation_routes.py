"""Planar simulation engine API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from earth.cosmology.engine import get_engine
from earth.simulation.planar_grid import sample_planar_grid

router = APIRouter(tags=["simulation"])


@router.get("/simulation/grid")
async def simulation_grid(
    size: int = Query(128, ge=32, le=512),
    field: str = Query("flow"),
    t_s: float | None = Query(None),
):
    engine = get_engine()
    return sample_planar_grid(
        size=size,
        field=field,
        t_s=t_s if t_s is not None else engine.t_sim,
        omega0=engine.omega0,
    )


@router.get("/simulation/state")
async def simulation_state():
    engine = get_engine()
    st = engine.state()
    st["domain"] = "planar_polar"
    st["engine_type"] = "udm_planar_simulation"
    return st