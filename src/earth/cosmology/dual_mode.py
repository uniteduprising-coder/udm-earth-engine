"""
Dual-mode reality engine — UDM vs Copernican (WGS84) comparison.

Competitive Advantage Blueprint §1.1 — parallel cosmologies on shared observational feed.
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology.chromatic import full_chromatic_synthesis
from earth.cosmology.coordinates import geo_to_cylindrical, project_site
from earth.cosmology.engine import CosmologyEngine, get_engine
from earth.cosmology import fields


def _udm_field_summary(lat: float, lon: float, t_s: float, engine: CosmologyEngine) -> dict[str, Any]:
    cyl = geo_to_cylindrical(lat, lon)
    r, th = cyl["r_mi"], cyl["theta_rad"]
    P = engine.params
    return {
        "r_mi": r,
        "theta_rad": th,
        "I_glow_cd": round(fields.glow_intensity(r, th, t_s, P), 2),
        "B_stat_nT": round(fields.B_stat(r, th, P) * 1e9, 2),
        "rho_a": round(fields.rho_a_field(r, th, t_s, P), 12),
        "Omega0": round(engine.omega0, 6),
    }


def compare_cosmologies(
    lat: float,
    lon: float,
    *,
    t_s: float = 0.0,
    engine: CosmologyEngine | None = None,
) -> dict[str, Any]:
    """Side-by-side UDM and Copernican projections with divergence metrics."""
    engine = engine or get_engine()
    udm = project_site(lat, lon, mode="udm_v5")
    cop = project_site(lat, lon, mode="wgs84")
    chrom_udm = full_chromatic_synthesis(lat=lat, lon=lon, t_s=t_s)
    udm_fields = _udm_field_summary(lat, lon, t_s, engine)

    d_lat = abs(udm["lat_udm"] - cop["lat_udm"])
    d_lon = abs(udm["lon_udm"] - cop["lon_udm"])
    if d_lon > 180:
        d_lon = 360 - d_lon

    return {
        "mode": "compare",
        "active_cosmology": "UDM v5.2α",
        "location": {"lat": lat, "lon": lon},
        "t_s": t_s,
        "udm": {
            "projection": udm,
            "fields": udm_fields,
            "chromatic": chrom_udm.get("summary", {}),
        },
        "copernican": {
            "projection": cop,
            "note": "WGS84 passthrough — standard heliocentric map baseline",
        },
        "divergence": {
            "position_delta_deg": round(math.sqrt(d_lat**2 + d_lon**2), 6),
            "lat_delta_deg": round(d_lat, 6),
            "lon_delta_deg": round(d_lon, 6),
            "glow_udm_only_cd": udm_fields["I_glow_cd"],
            "predictions_diverge": d_lat > 0.001 or udm_fields["I_glow_cd"] > 100,
        },
    }


def difference_map(
    lat: float,
    lon: float,
    *,
    span_deg: float = 5.0,
    grid: int = 5,
    t_s: float = 0.0,
) -> dict[str, Any]:
    """Sample grid of UDM vs Copernican position deltas around a point."""
    grid = max(3, min(grid, 11))
    step = span_deg / (grid - 1) if grid > 1 else 0.0
    cells: list[dict[str, Any]] = []
    max_delta = 0.0
    for i in range(grid):
        for j in range(grid):
            la = lat - span_deg / 2 + i * step
            lo = lon - span_deg / 2 + j * step
            udm = project_site(la, lo, mode="udm_v5")
            cop = project_site(la, lo, mode="wgs84")
            d_lat = abs(udm["lat_udm"] - cop["lat_udm"])
            d_lon = abs(udm["lon_udm"] - cop["lon_udm"])
            if d_lon > 180:
                d_lon = 360 - d_lon
            delta = math.sqrt(d_lat**2 + d_lon**2)
            max_delta = max(max_delta, delta)
            cells.append(
                {
                    "lat": round(la, 4),
                    "lon": round(lo, 4),
                    "delta_deg": round(delta, 6),
                    "udm_glow_cd": round(
                        fields.glow_intensity(
                            udm["r_mi"], udm["theta_rad"], t_s, get_engine().params
                        ),
                        1,
                    ),
                }
            )
    return {
        "center": {"lat": lat, "lon": lon},
        "span_deg": span_deg,
        "grid": grid,
        "max_delta_deg": round(max_delta, 6),
        "cells": cells,
    }


def reality_mode_summary(engine: CosmologyEngine | None = None) -> dict[str, Any]:
    """Dashboard header payload for Reality Mode selector."""
    from earth.cosmology.validation import run_validation

    engine = engine or get_engine()
    report = run_validation(engine)
    passed = report["passed"]
    total = report["total_checks"]
    return {
        "modes": ["copernican", "udm", "split", "overlay"],
        "active": "udm",
        "cosmology_version": "5.2α",
        "observational_consistency": f"{passed}/{total} checks passed",
        "score_pct": round(100 * passed / total, 1),
        "validation": report,
    }