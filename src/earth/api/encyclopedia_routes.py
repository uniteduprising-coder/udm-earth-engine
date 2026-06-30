"""UDM Master Encyclopedia API routes."""

from __future__ import annotations

from fastapi import APIRouter

from earth.cosmology.encyclopedia import ingest_encyclopedia, load_jerk_catalogue, provenance_summary

router = APIRouter(tags=["encyclopedia"])


@router.get("/encyclopedia")
async def get_encyclopedia():
    return provenance_summary()


@router.get("/encyclopedia/jerks")
async def get_jerk_catalogue():
    return {"jerks": load_jerk_catalogue()}


@router.post("/encyclopedia/ingest")
async def run_encyclopedia_ingest():
    return ingest_encyclopedia()