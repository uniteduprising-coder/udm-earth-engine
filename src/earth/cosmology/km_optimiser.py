"""
K_m auto-tune sensitivity sweep (v5.2β §2.4 mass exchange).
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology.below_cell import twin_cell_mass_balance
from earth.cosmology.params import load_params


def km_sweep(
    *,
    center: float | None = None,
    sweep_range: float | None = None,
    steps: int = 11,
) -> dict[str, Any]:
    """±sweep_range sensitivity sweep around nominal K_m."""
    P = load_params()
    km0 = center if center is not None else P.get("Km", P.get("K_m", 0.0013))
    span = sweep_range if sweep_range is not None else P.get("Km_sweep_range", 0.5)
    target_rmse = P.get("Km_rmse_target", 0.05)

    results: list[dict[str, Any]] = []
    best = {"km": km0, "rmse": float("inf")}

    for i in range(steps):
        frac = -span + (2 * span * i / max(steps - 1, 1))
        km = km0 * (1.0 + frac)
        P_test = {**P, "Km": km, "K_m": km, "Km_below": -km}
        balance = twin_cell_mass_balance(P_test)
        rmse = abs(balance["net_mass_exchange"]) + abs(balance["net_hydro_flux"]) * 0.01
        entry = {
            "Km": round(km, 6),
            "net_mass_exchange": balance["net_mass_exchange"],
            "steady_state": balance["steady_state"],
            "rmse": round(rmse, 6),
        }
        results.append(entry)
        if rmse < best["rmse"]:
            best = {"km": km, "rmse": rmse}

    optimal_passes = best["rmse"] <= target_rmse
    return {
        "nominal_Km": km0,
        "sweep_range": span,
        "target_rmse": target_rmse,
        "optimal_Km": round(best["km"], 6),
        "optimal_rmse": round(best["rmse"], 6),
        "optimal_passes": optimal_passes,
        "sweep": results,
        "recommendation": (
            f"Use Km={best['km']:.6f}" if optimal_passes else f"Keep Km={km0} (RMSE={best['rmse']:.4f})"
        ),
    }