from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from earth.config import get_settings
from earth.handlers.registry import HandlerRegistry
from earth.handlers.seed_layers import seed_layer_geojson
from earth.handlers.sites_kml import get_layer_payload
from earth.projection.udm import project_flat

router = APIRouter()
registry = HandlerRegistry(get_settings())


@router.get("/health")
async def health():
    return {
        "service": "udm-earth-engine",
        "status": "ok",
        "time": datetime.now(UTC).isoformat(),
        "projection": "udm_v5",
        "cosmology_engine": "5.2β",
        "coordinate_basis": "cylindrical (r, theta, z)",
    }


@router.get("/v1/feeds")
async def list_feeds():
    return {"feeds": get_settings().load_feeds()}


@router.get("/v1/layers")
async def list_layers():
    layers = get_settings().load_layers()
    return {
        "layers": [
            {
                "id": l["id"],
                "label": l["label"],
                "icon": l.get("icon", ""),
                "color": l.get("color", "#64748b"),
                "handler": l.get("handler"),
                "enabled": l.get("enabled", True),
            }
            for l in layers
            if l.get("enabled", True)
        ]
    }


@router.get("/v1/layer/{layer_id}")
async def get_layer(
    layer_id: str,
    lst_hours: float = Query(12.0, ge=0, le=24),
    mode: str = Query("udm_flat"),
):
    settings = get_settings()
    layers = {l["id"]: l for l in settings.load_layers()}
    if layer_id not in layers:
        raise HTTPException(404, "Unknown layer")

    layer = layers[layer_id]
    handler_name = layer.get("handler", "")

    if handler_name == "sites_kml":
        cache_path = settings.cache_path / "sites_layers.json"
        if cache_path.exists():
            record = json.loads(cache_path.read_text(encoding="utf-8"))
            geo = record.get("payload", {}).get("layers", {}).get(layer_id)
            if geo:
                return {"layer_id": layer_id, "source": "cache", "geojson": geo}
        geo = get_layer_payload(settings, layer_id, lst_hours=lst_hours)
        if geo:
            return {"layer_id": layer_id, "source": "computed", "geojson": geo}
        raise HTTPException(404, "Layer empty — run refresh")

    cache_map = {
        "suppressed_events": "suppressed_events",
        "masonic_temples": "masonic_temples",
        "forensic_bridge": "forensic_mc04_mc05",
    }
    if handler_name in cache_map:
        cid = cache_map[handler_name] if handler_name != "forensic_bridge" else "forensic_mc04_mc05"
        path = settings.cache_path / f"{cid}.json"
        if not path.exists() and handler_name in ("suppressed_events", "masonic_temples"):
            seed_file = "suppressed_events.json" if handler_name == "suppressed_events" else "masonic_temples.json"
            geo = seed_layer_geojson(settings, layer_id, seed_file)
            return {"layer_id": layer_id, "source": "seed", "geojson": geo}
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            payload = record.get("payload", record)
            return {
                "layer_id": layer_id,
                "source": "cache",
                "fetched_at": record.get("fetched_at"),
                "geojson": payload.get("geojson"),
                "meta": {k: v for k, v in payload.items() if k != "geojson"},
            }

    raise HTTPException(404, "Layer data not available")


@router.get("/v1/stream/{feed_id}")
async def stream_feed(feed_id: str):
    settings = get_settings()
    path = settings.cache_path / f"{feed_id}.json"
    if not path.exists():
        feeds = {f["id"]: f for f in settings.load_feeds()}
        if feed_id not in feeds:
            raise HTTPException(404, "Unknown feed")
        feed = feeds[feed_id]
        handler = registry.get(feed["handler"])
        record = await handler.fetch(feed)
        return record
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/v1/refresh")
async def refresh_all():
    from earth.main import get_scheduler

    sched = get_scheduler()
    if sched is None:
        raise HTTPException(503, "Scheduler not ready")
    ids = await sched.refresh_all()
    return {"ok": True, "refreshed": ids, "time": datetime.now(UTC).isoformat()}


@router.post("/v1/refresh/{target_id}")
async def refresh_one(target_id: str):
    settings = get_settings()
    feeds = {f["id"]: f for f in settings.load_feeds()}
    if target_id in feeds:
        handler = registry.get(feeds[target_id]["handler"])
        record = await handler.fetch(feeds[target_id])
        return {"ok": True, "target": target_id, "record": record}

    layers = {l["id"]: l for l in settings.load_layers()}
    if target_id in layers:
        handler_name = layers[target_id].get("handler", "")
        if handler_name in registry._map:
            handler = registry.get(handler_name)
            record = await handler.fetch({"id": target_id, "enabled": True})
            return {"ok": True, "target": target_id, "record": record}

    raise HTTPException(404, "Unknown feed or layer")


@router.get("/v1/projection/project")
async def projection_project(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    lst_hours: float = Query(12.0, ge=0, le=24),
    mode: str = Query("udm_flat"),
):
    proj_mode = "wgs84" if mode == "wgs84" else "udm_flat"
    return project_flat(lat, lon, lst_hours=lst_hours, mode=proj_mode)


@router.get("/v1/udm/constants")
async def udm_constants():
    from earth.projection.udm import (
        ALPHA_ANTI_H,
        KAPPA_COUPLING,
        PHI_NODE_DEG,
        PHI_WIND_DEG,
        A_CALIB_MMHG,
    )

    return {
        "equations": {
            "winding": "W(phi) = cos(phi - PHI_WIND_DEG)",
            "pressure": "A(phi) = 0.1699 * W(phi)",
            "master_relation": "Y = G * kappa * W(phi) * cos(LST - ALPHA_ANTI_H)",
        },
        "constants": {
            "PHI_WIND_DEG": PHI_WIND_DEG,
            "PHI_NODE_DEG": PHI_NODE_DEG,
            "ALPHA_ANTI_H": ALPHA_ANTI_H,
            "KAPPA_COUPLING": KAPPA_COUPLING,
            "A_CALIB_MMHG": A_CALIB_MMHG,
        },
    }