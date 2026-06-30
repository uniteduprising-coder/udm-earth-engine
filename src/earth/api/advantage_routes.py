"""
Competitive Advantage Blueprint API — dual mode, spectral, predictions, replay, ingestion, WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Query, WebSocket, WebSocketDisconnect

from earth.config import ROOT
from earth.cosmology.dual_mode import compare_cosmologies, difference_map, reality_mode_summary
from earth.cosmology.engine import get_engine
from earth.cosmology.ingestion import ingestion_status, run_ingestion_cycle
from earth.cosmology.predictions import (
    OBSERVABLES,
    generate_prediction,
    list_predictions,
    observation_network,
    submit_prediction,
)
from earth.cosmology.replay import replay_metadata, replay_state, replay_tick
from earth.cosmology.spectral import render_spectral
from earth.cosmology.telemetry import pack_physics_frame, pack_validation_frame, telemetry_json_frame
from earth.cosmology.validation import run_validation

router = APIRouter(tags=["advantage"])

ADVANTAGE_JSON = ROOT / "public" / "data" / "cosmology" / "advantage.json"


@router.get("/advantage/summary")
async def advantage_summary():
    return reality_mode_summary()


@router.get("/advantage/dual-mode")
async def dual_mode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    t_s: float = Query(0.0, ge=0),
    view: str = Query("compare", pattern="^(compare|split|overlay)$"),
):
    base = compare_cosmologies(lat, lon, t_s=t_s)
    base["view"] = view
    if view == "overlay":
        base["difference_map"] = difference_map(lat, lon, grid=5, t_s=t_s)
    return base


@router.get("/advantage/difference-map")
async def dual_difference_map(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    span_deg: float = Query(5.0, gt=0, le=30),
    grid: int = Query(5, ge=3, le=11),
    t_s: float = Query(0.0, ge=0),
):
    return difference_map(lat, lon, span_deg=span_deg, grid=grid, t_s=t_s)


@router.get("/advantage/spectral")
async def spectral_render(
    cosmology: str = Query("udm", pattern="^(udm|copernican)$"),
    melanin: float = Query(12.0, ge=0, le=100),
    hemoglobin: float = Query(85.0, ge=0, le=100),
    aether_glow: float = Query(1.0, ge=0, le=3),
):
    return render_spectral(
        cosmology=cosmology,
        melanin=melanin,
        hemoglobin=hemoglobin,
        aether_glow_factor=aether_glow,
    )


@router.get("/advantage/predict")
async def predict(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    r_mi: float | None = Query(None, ge=0),
    theta_rad: float | None = Query(None),
    t_s: float = Query(0.0, ge=0),
    observable: str = Query("glow"),
    melanin_pct: float = Query(12.0, ge=0, le=100),
):
    if observable not in OBSERVABLES:
        observable = "glow"
    return generate_prediction(
        lat=lat,
        lon=lon,
        r_mi=r_mi,
        theta_rad=theta_rad,
        t_s=t_s,
        observable=observable,
        melanin_pct=melanin_pct,
    )


@router.get("/advantage/predictions")
async def predictions_market(active_only: bool = Query(True)):
    return list_predictions(active_only=active_only)


@router.post("/advantage/predictions/submit")
async def predictions_submit(body: dict[str, Any] = Body(...)):
    return submit_prediction(
        observable=body.get("observable", "glow"),
        r_mi=float(body.get("r_mi", 70)),
        theta_rad=float(body.get("theta_rad", 0.785)),
        predicted_value=str(body.get("predicted", "")),
        stake_points=int(body.get("stake_points", 100)),
        submitter=str(body.get("submitter", "anonymous")),
        window_hours=int(body.get("window_hours", 48)),
    )


@router.get("/advantage/observations/network")
async def observations_network():
    return observation_network()


@router.get("/advantage/replay")
async def replay_info(event_id: str = Query("soviet_1982")):
    return replay_metadata(event_id)


@router.get("/advantage/replay/state")
async def replay_current(
    event_id: str = Query("soviet_1982"),
    t_offset_s: float = Query(0.0, ge=0),
):
    return replay_state(event_id, t_offset_s=t_offset_s)


@router.post("/advantage/replay/step")
async def replay_advance(
    event_id: str = Query("soviet_1982"),
    t_offset_s: float = Query(0.0, ge=0),
    delta_s: float = Query(852.0, ge=0),
):
    return replay_tick(event_id, t_offset_s + delta_s)


@router.get("/advantage/ingestion")
async def ingestion():
    return ingestion_status()


@router.post("/advantage/ingestion/run")
async def ingestion_run(body: dict[str, Any] | None = Body(None)):
    sources = body.get("sources") if body else None
    return run_ingestion_cycle(sources=sources)


def export_advantage_json() -> Path:
    """Bake advantage dashboard payload for edge CDN."""
    engine = get_engine()
    payload = {
        "version": "5.2β",
        "blueprint": "competitive_advantage",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": reality_mode_summary(engine),
        "spectral_udm": render_spectral(cosmology="udm"),
        "spectral_copernican": render_spectral(cosmology="copernican"),
        "predictions": list_predictions(),
        "observation_network": observation_network(),
        "replay": replay_metadata("soviet_1982"),
        "ingestion": ingestion_status(),
    }
    ADVANTAGE_JSON.parent.mkdir(parents=True, exist_ok=True)
    ADVANTAGE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return ADVANTAGE_JSON


@router.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    """Live solver telemetry — binary frames + JSON fallback."""
    await websocket.accept()
    engine = get_engine()
    binary = websocket.query_params.get("binary", "0") == "1"
    try:
        while True:
            ts = time.time()
            engine.macro_step_tick()
            state = engine.state()
            validation = run_validation(engine)

            if binary:
                await websocket.send_bytes(pack_physics_frame(ts, state))
                await websocket.send_bytes(pack_validation_frame(ts, validation))
            else:
                frame = telemetry_json_frame(ts, state=state, validation=validation)
                await websocket.send_json(frame)

            await asyncio.sleep(engine.params.get("DT_MACRO", 15))
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close()