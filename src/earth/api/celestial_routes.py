"""North Axis Aperture and Celestial Governance API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from earth.cosmology.celestial_governance import (
    classification_table,
    evaluate_observer,
    governance_hierarchy,
    governance_summary,
    measurement_feeds,
)

router = APIRouter(tags=["celestial"])


@router.get("/celestial/governance")
async def get_governance():
    return governance_summary()


@router.get("/celestial/hierarchy")
async def get_hierarchy():
    return {"hierarchy": governance_hierarchy()}


@router.get("/celestial/classification")
async def get_classification():
    return {"classification_table": classification_table()}


@router.get("/celestial/measurements")
async def get_measurements():
    return {"measurement_feeds": measurement_feeds()}


@router.get("/celestial/north-axis")
async def get_north_axis(
    lat: float = Query(..., description="Observer field-latitude φ (degrees)"),
    R_f: float | None = Query(None, description="Firmament/refraction contribution (deg)"),
    A_o: float | None = Query(None, description="Aperture offset contribution (deg)"),
    V_p: float | None = Query(None, description="Polar vortex distortion contribution (deg)"),
):
    return evaluate_observer(phi_deg=lat, R_f=R_f, A_o=A_o, V_p=V_p)