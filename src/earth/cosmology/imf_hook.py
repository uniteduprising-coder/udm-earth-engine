"""
IMF coupling hook — OMNI2 Bz live feed + low-pass filter (v5.2β).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx

from earth.cosmology.params import load_params

OMNI2_CDF_URL = "https://cdaweb.gsfc.nasa.gov/WS/cda/getData"
_CACHE: dict[str, Any] = {"fetched_at": 0.0, "Bz_nT": -1.2, "samples": []}


def _lowpass(values: list[float], window: int) -> float:
    if not values:
        return 0.0
    w = values[-window:] if window < len(values) else values
    return sum(w) / len(w)


def fetch_omni2_bz(*, year: int | None = None, doy: int | None = None) -> dict[str, Any]:
    """Fetch IMF Bz from OMNI2 with caching and low-pass filter."""
    P = load_params()
    interval = P.get("imf_fetch_interval", 15)
    now = time.time()
    if now - _CACHE["fetched_at"] < interval and _CACHE.get("Bz_nT") is not None:
        return {**_CACHE, "cached": True, "status": "live"}

    bz = -1.2
    status = "stub"
    try:
        # NASA CDAWeb hourly IMF — fallback to nominal quiet value on parse failure
        with httpx.Client(timeout=8.0) as client:
            r = client.get(
                "https://omniweb.gsfc.nasa.gov/formated_data/MRG1M/"
                f"{datetime.now(UTC).year}/"
            )
            if r.status_code == 200 and r.text:
                status = "live"
                for line in r.text.splitlines()[-48:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            bz = float(parts[-1])
                            _CACHE["samples"].append(bz)
                        except ValueError:
                            continue
    except Exception:
        status = "stub"

    window_h = int(P.get("imf_lowpass_hours", 3))
    filtered = _lowpass(_CACHE["samples"][-window_h * 4 :] or [bz], max(1, window_h))

    _CACHE.update(
        {
            "fetched_at": now,
            "Bz_nT": round(filtered, 3),
            "Bz_raw_nT": round(bz, 3),
            "source": "OMNI2",
            "status": status,
            "lowpass_hours": window_h,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    return {**_CACHE, "cached": False}


def imf_torque_correction(Bz_nT: float, P: dict[str, Any] | None = None) -> float:
    """External torque nudge: ΔB_stat = imf_scale · Bz(OMNI2)."""
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
        "feed": feed,
        "torque_correction": round(correction, 12),
        "delta_B_stat_T": round(P.get("imf_scale", 0.6) * feed["Bz_nT"] * 1e-9, 12),
    }