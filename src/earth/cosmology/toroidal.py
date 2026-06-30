"""
UDM v5.2β — full toroidal domain, exterior void, three realms, view modes.
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology.below_cell import below_cell_sample, glow_below, twin_cell_mass_balance
from earth.cosmology import fields
from earth.cosmology.params import load_params


def domain_extents(P: dict[str, Any] | None = None) -> dict[str, Any]:
    P = P or load_params()
    z_max = P.get("z_max", P.get("z_roof", 700))
    z_t = -abs(P.get("z_T", 3200))
    r_disk = P["R_disk"]
    return {
        "version": "5.2β",
        "coordinate_basis": "cylindrical (r, θ, z) statute miles",
        "origin": "Rupes Nigra peak (North Pole, z=0)",
        "r_mi": {"min": P.get("r_sink_a", 0.005), "max": r_disk},
        "theta_rad": {"min": 0.0, "max": 2 * math.pi},
        "z_mi": {"min": z_t, "max": z_max},
        "r_base_mi": P["r_base"],
        "vertical_span_mi": z_max - z_t,
        "aspect_ratio": round(r_disk / (z_max - z_t), 2),
        "realms": {
            "upper": {"z_min": 0, "z_max": z_max, "name": "Firmament Dome"},
            "middle": {"z_min": -14, "z_max": 0, "name": "Equatorial Plane"},
            "lower": {"z_min": z_t, "z_max": -14, "name": "Below-Cell Abyss"},
        },
    }


def is_inside_domain(r: float, z: float, P: dict[str, Any] | None = None) -> bool:
    P = P or load_params()
    z_max = P.get("z_max", P.get("z_roof", 700))
    z_t = -abs(P.get("z_T", 3200))
    return (P.get("r_sink_a", 0.005) <= r <= P["R_disk"]) and (z_t <= z <= z_max)


def exterior_void_properties(P: dict[str, Any] | None = None) -> dict[str, Any]:
    P = P or load_params()
    return {
        "condition": "r > R_disk OR z > z_max OR z < z_T",
        "rho_kg_m3": P.get("void_rho", 1e12),
        "sigma_Sm": P.get("void_sigma", 0.0),
        "n_refractive": P.get("void_n", 1e6),
        "opacity": P.get("void_opacity", 1.0),
        "rendering": "absolute black — no emission, reflection, or transmission",
        "observational": [
            "Stars on inner firmament surface (z ≈ z_max)",
            "No luminaries outside shell",
            "All fields confined within toroidal domain",
        ],
    }


def boundary_conditions(P: dict[str, Any] | None = None) -> dict[str, Any]:
    P = P or load_params()
    z_max = P.get("z_max", 700)
    z_t = -abs(P.get("z_T", 3200))
    return {
        "r_disk": {"r_mi": P["R_disk"], "V_r": 0, "B_r": 0, "I_glow": 0, "n": "∞ TIR"},
        "z_max": {"z_mi": z_max, "d_dz": 0, "Phi_e": 0, "stars_embedded": True},
        "z_T": {"z_mi": z_t, "V_z": 0, "mirror_vortex": True},
    }


def field_sample_3d(
    r: float,
    theta: float,
    z: float,
    t: float,
    *,
    omega0: float = 2.45,
    P: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sample fields across full 3D toroidal domain."""
    P = P or load_params()
    inside = is_inside_domain(r, z, P)
    if not inside:
        return {
            "inside_domain": False,
            "realm": "exterior_void",
            "void": exterior_void_properties(P),
        }

    if z < 0:
        sample = below_cell_sample(r, theta, z, t, P)
        sample["inside_domain"] = True
        sample["upper_glow_cd"] = fields.glow_intensity(r, theta, t, P)
        return sample

    return {
        "inside_domain": True,
        "realm": "upper" if z > 0 else "equatorial",
        "r_mi": r,
        "theta_rad": theta,
        "z_mi": z,
        "t_s": t,
        "B_stat_T": fields.B_stat(r, theta, P),
        "rho_a": fields.rho_a_field(r, theta, t, P),
        "I_cd": fields.glow_intensity(r, theta, t, P),
        "I_below_cd": glow_below(r, theta, z, t, P) if z <= 0 else 0.0,
        "n_real": fields.n_firmament_real(z, P),
        "n_imag": fields.n_firmament_imag(z, P),
        "Omega_firm": fields.omega_firm(r, z, omega0, P),
        "V_h": {
            "r": fields.V_r_h(r, theta, P),
            "theta": fields.V_theta_h(r, P),
            "z": fields.V_z_h(z, P),
        },
        "V_a": {
            "r": fields.V_r_a(r, P),
            "theta": fields.V_theta_a(r, P),
        },
    }


VIEW_MODES = (
    "top",
    "underside",
    "toroidal",
    "cross_section",
    "observer",
    "dual_hemisphere",
)


def view_mode_config(mode: str = "top") -> dict[str, Any]:
    """Camera / layer configuration for each view mode."""
    P = load_params()
    d = domain_extents(P)
    configs = {
        "top": {
            "label": "Top View (Standard)",
            "camera": {"z_sign": 1, "offset_mi": 0},
            "layers": {"upper": True, "below": False, "void": False, "boundary": False},
        },
        "underside": {
            "label": "Underside View",
            "camera": {"z_sign": -1, "offset_mi": -2000, "up": [0, 0, -1]},
            "layers": {"upper": False, "below": True, "void": False, "boundary": False},
            "z_map": "z → −z, θ preserved",
        },
        "toroidal": {
            "label": "Toroidal Expansion",
            "camera": {
                "target": [0, 0, -1250],
                "distance_mi": 18000,
                "position_factor": [0.5, 0.3, 0.7],
            },
            "layers": {"upper": True, "below": True, "void": True, "boundary": True},
        },
        "cross_section": {
            "label": "Cross-Section Slice",
            "plane": "r-z",
            "layers": {"upper": True, "below": True, "island_roots": True},
        },
        "observer": {"label": "Observer Perspective", "first_person": True},
        "dual_hemisphere": {
            "label": "Dual Hemisphere",
            "split": "horizontal",
            "top_mode": "top",
            "bottom_mode": "underside",
        },
    }
    return {
        "mode": mode,
        "available": list(VIEW_MODES),
        **configs.get(mode, configs["top"]),
        "domain": d,
        "twin_cell": twin_cell_mass_balance(P),
    }


def toroidal_state(omega0: float = 2.45, t_s: float = 0.0) -> dict[str, Any]:
    """Aggregate toroidal engine state for API / telemetry."""
    P = load_params()
    anchor_r, anchor_th = 70.0, math.pi / 4
    return {
        "version": "5.2β",
        "domain": domain_extents(P),
        "void": exterior_void_properties(P),
        "boundaries": boundary_conditions(P),
        "twin_cell": twin_cell_mass_balance(P),
        "below_cell_anchor": below_cell_sample(anchor_r, anchor_th, -500.0, t_s, P),
        "upper_anchor": field_sample_3d(anchor_r, anchor_th, 0.0, t_s, omega0=omega0, P=P),
        "view_modes": list(VIEW_MODES),
    }