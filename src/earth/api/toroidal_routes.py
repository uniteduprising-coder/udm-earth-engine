"""
UDM v5.2β toroidal API — domain, below-cell, void, view modes, IMF, K_m, jerk.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from earth.cosmology.amr_scaffold import amr_config, amr_grid_summary
from earth.cosmology.below_cell import below_cell_sample, twin_cell_mass_balance
from earth.cosmology.imf_hook import imf_live_state
from earth.cosmology.jerk_crosscheck import jerk_crosscheck
from earth.cosmology.km_optimiser import km_sweep
from earth.cosmology.params import load_params
from earth.cosmology.toroidal import (
    VIEW_MODES,
    boundary_conditions,
    domain_extents,
    exterior_void_properties,
    field_sample_3d,
    toroidal_state,
    view_mode_config,
)

router = APIRouter(tags=["toroidal"])


@router.get("/toroidal/domain")
async def get_domain():
    return domain_extents()


@router.get("/toroidal/state")
async def get_toroidal_state(t_s: float = Query(0.0, ge=0)):
    return toroidal_state(t_s=t_s)


@router.get("/toroidal/void")
async def get_void():
    return exterior_void_properties()


@router.get("/toroidal/boundaries")
async def get_boundaries():
    return boundary_conditions()


@router.get("/toroidal/field")
async def get_field_3d(
    r_mi: float = Query(..., gt=0),
    theta_rad: float = Query(0.0),
    z_mi: float = Query(0.0),
    t_s: float = Query(0.0, ge=0),
):
    return field_sample_3d(r_mi, theta_rad, z_mi, t_s)


@router.get("/toroidal/below-cell")
async def get_below_cell(
    r_mi: float = Query(70.0, gt=0),
    theta_rad: float = Query(0.785),
    z_mi: float = Query(-500.0, le=0),
    t_s: float = Query(0.0, ge=0),
):
    return below_cell_sample(r_mi, theta_rad, z_mi, t_s, load_params())


@router.get("/toroidal/twin-cell")
async def get_twin_cell():
    return twin_cell_mass_balance(load_params())


@router.get("/toroidal/view-modes")
async def get_view_modes(mode: str = Query("top")):
    if mode not in VIEW_MODES:
        mode = "top"
    return view_mode_config(mode)


@router.get("/toroidal/imf")
async def get_imf():
    return imf_live_state()


@router.post("/toroidal/km/optimise")
async def optimise_km():
    return km_sweep()


@router.get("/toroidal/jerk")
async def get_jerk():
    return jerk_crosscheck()


@router.get("/toroidal/amr")
async def get_amr():
    return {"config": amr_config(), "grid": amr_grid_summary()}