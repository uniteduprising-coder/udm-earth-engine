"""Planar polar grid sampler for UDM simulation engine."""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology import fields
from earth.cosmology.engine import get_engine
from earth.cosmology.params import load_params


def _normalize_params(p: dict[str, Any]) -> dict[str, Any]:
    out = dict(p)
    if "rho0" in out and "rho_a0" not in out:
        out["rho_a0"] = out["rho0"]
    if "Omega0" in out and "Omega0_init" not in out:
        out["Omega0_init"] = out["Omega0"]
    return out


def sample_planar_grid(
    *,
    size: int = 128,
    field: str = "flow",
    t_s: float | None = None,
    omega0: float | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sample a scalar field on flat polar disk ρ∈[0,1], θ∈[0,2π)."""
    P = _normalize_params(params or load_params())
    engine = get_engine()
    t = engine.t_sim if t_s is None else t_s
    omega = engine.omega0 if omega0 is None else omega0
    r_earth = float(P["R_earth"])

    values: list[list[float]] = []
    vmax = 0.0
    for j in range(size):
        row: list[float] = []
        for i in range(size):
            dx = (i + 0.5) / size - 0.5
            dy = (j + 0.5) / size - 0.5
            dist = math.hypot(dx, dy)
            if dist > 0.5:
                row.append(float("nan"))
                continue
            rho = dist * 2.0
            theta = math.atan2(dx, dy)
            r_mi = max(rho * r_earth, P["r_sink"] + 1e-6)
            if field == "flow":
                vr = fields.V_r_h(r_mi, theta, P)
                vt = fields.V_theta_h(r_mi, P)
                v = math.hypot(vr, vt)
            elif field == "vr":
                v = abs(fields.V_r_h(r_mi, theta, P))
            elif field == "glow":
                v = fields.glow_intensity(r_mi, theta, t, P)
            elif field == "bstat":
                v = abs(fields.B_stat(r_mi, theta, P))
            elif field == "rhoa":
                v = abs(fields.rho_a_field(r_mi, theta, t, P))
            elif field == "emf":
                v = abs(fields.motional_emf(r_mi, theta, omega, P))
            else:
                v = 0.0
            row.append(v)
            vmax = max(vmax, v)
        values.append(row)

    return {
        "size": size,
        "field": field,
        "t_sim_s": t,
        "omega0": omega,
        "vmax": vmax,
        "values": values,
        "domain": "planar_polar",
        "rho_unit": "normalized_0_center_1_rim",
    }