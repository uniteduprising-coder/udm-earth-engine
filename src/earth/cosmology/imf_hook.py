"""
IMF coupling hook — live NOAA SWPC Bz feed (v5.2β / Master Encyclopedia 2026-06-30).

CORRECTED endpoint (verified live 2026-06-30):
  https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json

Dead endpoint (404): services.swpc.noaa.gov/json/omni/hourly.json
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx

from earth.cosmology.params import load_params

SWPC_MAG_1DAY_URL = "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json"
_CACHE: dict[str, Any] = {"fetched_at": 0.0, "Bz_nT": -1.2, "samples": [], "status": "stub"}


def _lowpass(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def fetch_omni2_bz(*, year: int | None = None, doy: int | None = None) -> dict[str, Any]:
    """Fetch live IMF Bz from NOAA SWPC mag-1-day feed."""
    P = load_params()
    interval = P.get("imf_fetch_interval", 15)
    now = time.time()
    if now - _CACHE["fetched_at"] < interval and _CACHE.get("status") == "live":
        return {**_CACHE, "cached": True}

    bz_raw = -1.2
    samples: list[float] = []
    status = "stub"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(SWPC_MAG_1DAY_URL)
            resp.raise_for_status()
            rows = resp.json()
            if isinstance(rows, list) and len(rows) > 1:
                header = rows[0]
                bz_idx = header.index("bz_gsm") if "bz_gsm" in header else -1
                if bz_idx >= 0:
                    for row in rows[1:]:
                        try:
                            val = float(row[bz_idx])
                            samples.append(val)
                        except (ValueError, IndexError, TypeError):
                            continue
                    if samples:
                        bz_raw = samples[-1]
                        status = "live"
    except Exception as exc:
        _CACHE["error"] = str(exc)
        status = "stub"

    window_min = int(P.get("imf_lowpass_hours", 3) * 60)
    filtered = _lowpass(samples, max(1, window_min))
    bz_filtered = filtered[-1] if filtered else bz_raw

    _CACHE.update(
        {
            "fetched_at": now,
            "source": "NOAA SWPC mag-1-day",
            "url": SWPC_MAG_1DAY_URL,
            "Bz_nT": round(bz_filtered, 3),
            "Bz_raw_nT": round(bz_raw, 3),
            "sample_count": len(samples),
            "status": status,
            "lowpass_hours": P.get("imf_lowpass_hours", 3),
            "timestamp": datetime.now(UTC).isoformat(),
            "note": "imf_scale=0.6 is T4 empirical placeholder (1973 Explorer-50 event)",
        }
    )
    _CACHE["samples"] = samples[-48:]
    return {**_CACHE, "cached": False}


def imf_torque_correction(Bz_nT: float, P: dict[str, Any] | None = None) -> float:
    """External torque nudge: ΔB_stat = imf_scale · Bz."""
    P = P or load_params()
    if not P.get("imf_coupling_enabled"):
        return 0.0
    scale = P.get("imf_scale", 0.6)
    return scale * Bz_nT * 1.0e-9


def imf_live_state() -> dict[str, Any]:
    """Full IMF coupling state for API."""
    P = load_params()
    feed = fetch_omni2_bz()
    correction = imf_torque_correction(feed["Bz_nT"], P)
    return {
        "enabled": P.get("imf_coupling_enabled", False),
        "imf_scale": P.get("imf_scale", 0.6),
        "tier": "T4",
        "feed": feed,
        "torque_correction": round(correction, 12),
        "delta_B_stat_T": round(P.get("imf_scale", 0.6) * feed["Bz_nT"] * 1e-9, 12),
    }


def refresh_imf(scale: float | None = None, lowpass_hours: float | None = None) -> list[float]:
    """Compatibility wrapper for encyclopedia imf_hook.py execution."""
    P = load_params()
    if scale is not None:
        P = {**P, "imf_scale": scale}
    if lowpass_hours is not None:
        P = {**P, "imf_lowpass_hours": lowpass_hours}
    feed = fetch_omni2_bz()
    delta = [P.get("imf_scale", 0.6) * v * 1e-9 for v in feed.get("samples", [feed["Bz_nT"]])]
    return delta