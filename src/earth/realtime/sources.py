"""Source health checks and live data pulls (overlay/field only)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from earth.realtime.paths import CONFIG, DATA, LOGS


def load_sources_config() -> dict[str, Any]:
    with (CONFIG / "sources.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def _probe(url: str, timeout: float = 15.0) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url)
            return {
                "status": "online" if r.status_code == 200 else "malformed",
                "http_code": r.status_code,
                "bytes": len(r.content),
            }
    except httpx.TimeoutException:
        return {"status": "stale", "error": "timeout"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


async def check_all_sources() -> dict[str, Any]:
    cfg = load_sources_config()
    results: dict[str, Any] = {}
    for name, src in cfg.get("sources", {}).items():
        if src.get("type") == "json":
            ep = src.get("endpoints", {})
            url = ep.get("mag") or src.get("base_url", "")
        elif src.get("type") == "txt":
            url = src.get("url", "")
        elif src.get("type") == "arcgis_rest_wms":
            url = src.get("rest_url", "") + "?f=pjson"
        elif src.get("type") == "wmts_wms":
            url = src.get("wms", "") + "?SERVICE=WMS&REQUEST=GetCapabilities"
        elif src.get("type") == "user_supplied":
            results[name] = {"status": "needs_manual_review", "geometry_policy": src.get("geometry_policy")}
            continue
        else:
            url = src.get("url", "")
        if url:
            results[name] = {**await _probe(url), "geometry_policy": src.get("geometry_policy")}
        else:
            results[name] = {"status": "needs_manual_review"}

    out = {
        "checked_at": datetime.now(UTC).isoformat(),
        "sources": results,
    }
    (LOGS / "source_status.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


async def pull_swpc() -> dict[str, Any]:
    """Pull and normalize NOAA SWPC field inputs."""
    endpoints = {
        "mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json",
        "plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json",
        "kp": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
        "aurora": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
    }
    pulled: dict[str, Any] = {"pulled_at": datetime.now(UTC).isoformat(), "files": {}}
    raw_dir = DATA / "swpc" / "raw"
    norm_dir = DATA / "swpc" / "normalized"

    async with httpx.AsyncClient(timeout=20.0) as client:
        for key, url in endpoints.items():
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    pulled["files"][key] = {"ok": False, "status": r.status_code}
                    continue
                data = r.json()
                raw_path = raw_dir / f"{key}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.json"
                raw_path.write_text(json.dumps(data), encoding="utf-8")
                norm: dict[str, Any] = {"source": url, "key": key}
                if key == "mag" and isinstance(data, list) and len(data) > 1:
                    last = data[-1]
                    norm["bz_gsm_nT"] = float(last[3]) if len(last) > 3 else None
                    norm["time_tag"] = last[0]
                elif key == "kp" and isinstance(data, list) and len(data) > 1:
                    norm["kp"] = last[1] if isinstance(last, list) else last
                pulled["files"][key] = {"ok": True, "raw": str(raw_path), "normalized": norm}
                (norm_dir / f"{key}_latest.json").write_text(json.dumps(norm, indent=2), encoding="utf-8")
            except Exception as e:
                pulled["files"][key] = {"ok": False, "error": str(e)}

    return pulled


async def pull_gfz_kp() -> dict[str, Any]:
    url = "https://www-app3.gfz-potsdam.de/kp_index/Kp_ap_Ap_SN_F107_nowcast.txt"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                path = DATA / "gfz_kp" / f"kp_nowcast_{datetime.now(UTC).strftime('%Y%m%d')}.txt"
                path.write_text(r.text, encoding="utf-8")
                return {"ok": True, "path": str(path), "lines": len(r.text.splitlines())}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "status": "http_error"}