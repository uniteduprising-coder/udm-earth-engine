"""
IMF coupling hook — OMNI2 Bz injector (v5.2α §8, engineering task).

Non-blocking: disabled by default via imf_coupling_enabled in params.yml.
"""

from __future__ import annotations

from typing import Any

OMNI2_URL = "https://omniweb.gsfc.nasa.gov/spy/omni2"


def fetch_omni2_bz(*, year: int = 2024, doy: int = 1) -> dict[str, Any]:
    """Fetch IMF Bz sample from OMNI2 (stub — returns cached nominal quiet value)."""
    return {
        "source": "OMNI2",
        "year": year,
        "doy": doy,
        "Bz_nT": -1.2,
        "status": "stub",
        "note": "Enable imf_coupling_enabled and wire live OMNI2 parser for production",
    }


def imf_torque_correction(Bz_nT: float, P: dict[str, Any]) -> float:
    """Optional external torque nudge from solar wind Bz (engineering)."""
    if not P.get("imf_coupling_enabled"):
        return 0.0
    coupling = P.get("imf_coupling", 1.0e8)
    return coupling * Bz_nT * 1.0e-9