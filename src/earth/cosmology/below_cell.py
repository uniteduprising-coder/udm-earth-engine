"""
UDM v5.2β — below-cell hemisphere dynamics (mirror vortex, aether, island roots).
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology import fields


def _z_below(z: float) -> float:
    """Positive depth below equatorial plane."""
    return max(0.0, -z)


def V_theta_h_below(r: float, z: float, P: dict[str, Any]) -> float:
    """Counter-rotating hydro tangential velocity."""
    if z >= 0:
        return 0.0
    shear = 500.0
    return -fields.V_theta_h(r, P) * math.tanh(_z_below(z) / shear)


def V_r_h_below(r: float, z: float, P: dict[str, Any]) -> float:
    """Upwelling radial velocity in below cell."""
    if z >= 0:
        return 0.0
    shear = 500.0
    return abs(fields.V_r_h(r, 0.0, P)) * math.tanh(_z_below(z) / shear)


def V_z_h_below(r: float, z: float, P: dict[str, Any]) -> float:
    """Below-cell vertical velocity."""
    z_t = abs(P.get("z_T", 3200))
    w_b = P.get("W_b", 0.015)
    if z >= 0 or _z_below(z) > 500:
        return 0.0
    return -w_b * (_z_below(z) / z_t)


def V_theta_a_below(r: float, z: float, P: dict[str, Any]) -> float:
    if z >= 0:
        return 0.0
    shear = 300.0
    return -fields.V_theta_a(r, P) * math.tanh(_z_below(z) / shear)


def rho_a_below(r: float, theta: float, z: float, t: float, P: dict[str, Any]) -> float:
    """Below-cell aether density — denser with depth, π phase-shifted wave."""
    if z >= 0:
        return 0.0
    z_t = abs(P.get("z_T", 3200))
    factor = P.get("rho_below_factor", 0.3)
    base = fields.rho_a_field(r, theta, t, P) * (1.0 + factor * (_z_below(z) / z_t))
    phase = P.get("phase_shift_below", math.pi)
    m = P.get("m_a_below", P.get("m_a", 4))
    omega = P.get("omega_a_below", P.get("omega_a", 0.007371))
    return base * math.cos(m * theta + omega * t + phase)


def glow_below(r: float, theta: float, z: float, t: float, P: dict[str, Any]) -> float:
    """Abyssal green luminescence — exponentially dimmer with depth."""
    if z >= 0:
        return 0.0
    scale = P.get("glow_below_scale", 400.0)
    upper = fields.glow_intensity(r, theta, t, P)
    return upper * math.exp(-_z_below(z) / scale)


def sigma_iso_at_z(z: float, P: dict[str, Any]) -> float:
    """Island root conductivity decay with depth."""
    if z >= 0:
        return P["sigma_iso"]
    depth_scale = P.get("sigma_iso_depth_scale", 10.0)
    return P["sigma_iso"] * math.exp(-_z_below(z) / depth_scale)


def island_root_current_density(z: float, P: dict[str, Any]) -> float:
    """Normalized current density at island root depth."""
    half_depth = P.get("d_iso", P.get("island_depth", 14.0)) / 2.0
    if _z_below(z) > half_depth:
        return 0.1
    return math.exp(-_z_below(z) / P.get("sigma_iso_depth_scale", 10.0))


def below_cell_sample(
    r: float,
    theta: float,
    z: float,
    t: float,
    P: dict[str, Any],
) -> dict[str, Any]:
    """Full below-cell field sample at (r, θ, z)."""
    return {
        "r_mi": r,
        "theta_rad": theta,
        "z_mi": z,
        "t_s": t,
        "realm": "below_cell" if z < -14 else ("equatorial" if z >= -14 and z <= 0 else "upper"),
        "V_h": {
            "theta": V_theta_h_below(r, z, P),
            "r": V_r_h_below(r, z, P),
            "z": V_z_h_below(r, z, P),
        },
        "V_a": {"theta": V_theta_a_below(r, z, P)},
        "rho_a": rho_a_below(r, theta, z, t, P),
        "I_cd": glow_below(r, theta, z, t, P),
        "sigma_iso": sigma_iso_at_z(z, P),
        "island_current_norm": island_root_current_density(z, P),
        "nu_b": P.get("nu_b", 5.9e-5),
        "nu_a_below": P.get("nu_a_below", 5.9e-5),
    }


def twin_cell_mass_balance(P: dict[str, Any]) -> dict[str, Any]:
    """Verify closed toroidal mass circulation (net zero accumulation)."""
    km_up = P.get("K_m", P.get("Km", 0.0013))
    km_lo = P.get("Km_below", -0.0013)
    q_h = P.get("Q_h", 0.87)
    q_b = P.get("Q_b", P.get("Q_B", -0.87))
    q_a = P.get("Q_a", 0.104)
    net_exchange = km_up + km_lo
    net_hydro = q_h + q_b
    return {
        "Q_h": q_h,
        "Q_b": q_b,
        "Q_a": q_a,
        "Km_upper": km_up,
        "Km_below": km_lo,
        "net_mass_exchange": round(net_exchange, 6),
        "net_hydro_flux": round(net_hydro, 6),
        "steady_state": abs(net_exchange) < 1e-9 and abs(net_hydro) < 1e-9,
    }