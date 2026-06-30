"""
North Axis Aperture, Optical Stars, and Jovian-Saturnian Governance Layer.
Source: docs/North_Axis_Aperture_and_Celestial_Governance.md + config/celestial_governance.yaml
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from earth.config import ROOT

GOVERNANCE_DOC = ROOT / "docs" / "North_Axis_Aperture_and_Celestial_Governance.md"
GOVERNANCE_YAML = ROOT / "config" / "celestial_governance.yaml"


def load_governance_config() -> dict[str, Any]:
    if not GOVERNANCE_YAML.exists():
        return {}
    with GOVERNANCE_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def north_star_apparent_altitude(
    phi_deg: float,
    R_f: float = 0.0,
    A_o: float = 0.0,
    V_p: float = 0.0,
) -> float:
    """α_N = φ + R_f + A_o + V_p — field-angle projection of axis aperture register."""
    return round(phi_deg + R_f + A_o + V_p, 4)


def latitude_altitude_curve(
    latitudes: list[float] | None = None,
    R_f: float = 0.0,
    A_o: float = 0.0,
    V_p: float = 0.0,
) -> list[dict[str, float]]:
    """Sample α_N vs φ for validation against observed North Star altitude rule."""
    if latitudes is None:
        latitudes = [-60.0, -30.0, 0.0, 30.0, 45.0, 60.0, 90.0]
    return [
        {
            "phi_deg": lat,
            "alpha_N_deg": north_star_apparent_altitude(lat, R_f, A_o, V_p),
            "residual_deg": round(
                north_star_apparent_altitude(lat, R_f, A_o, V_p) - lat, 4
            ),
        }
        for lat in latitudes
    ]


def governance_hierarchy() -> list[str]:
    cfg = load_governance_config()
    return list(cfg.get("hierarchy", []))


def classification_table() -> list[dict[str, str]]:
    cfg = load_governance_config()
    return list(cfg.get("classification_table", []))


def measurement_feeds() -> dict[str, list[str]]:
    cfg = load_governance_config()
    out: dict[str, list[str]] = {}
    for key in (
        "north_axis_aperture",
        "stellar_lattice",
        "optical_planets",
        "saturn",
        "jupiter",
        "polar_vortex",
    ):
        section = cfg.get(key, {})
        feeds = section.get("measurement_feeds")
        if feeds:
            out[key] = list(feeds)
    return out


def governance_summary() -> dict[str, Any]:
    """Machine-readable governance layer for API and edge bake."""
    cfg = load_governance_config()
    defaults = cfg.get("north_axis_aperture", {}).get("defaults", {})
    R_f = float(defaults.get("R_f", 0.0))
    A_o = float(defaults.get("A_o", 0.0))
    V_p = float(defaults.get("V_p", 0.0))

    return {
        "document": cfg.get("document", "North Axis Aperture and Celestial Governance"),
        "compiled": cfg.get("compiled", "2026-06-30"),
        "version": cfg.get("version", "5.2β"),
        "north_axis_aperture": {
            "class": "axis_aperture_register",
            "alias": "North Fixed Star",
            "function": "visible registration of northern axis aperture — axial, not luminous",
            "formula": "α_N = φ + R_f + A_o + V_p",
            "defaults": {"R_f": R_f, "A_o": A_o, "V_p": V_p},
            "reference_chain": cfg.get("north_axis_aperture", {}).get("reference_chain", []),
        },
        "stellar_lattice": cfg.get("stellar_lattice", {}),
        "optical_planets": cfg.get("optical_planets", {}),
        "saturn": cfg.get("saturn", {}),
        "jupiter": cfg.get("jupiter", {}),
        "sun_moon": cfg.get("sun_moon", {}),
        "polar_vortex": cfg.get("polar_vortex", {}),
        "hierarchy": governance_hierarchy(),
        "classification_table": classification_table(),
        "measurement_feeds": measurement_feeds(),
        "working_statement": (
            "North Fixed Star = axis aperture orientation lock. "
            "Stars = fixed optical lattice. Most planets = ecliptic optical nodes. "
            "Saturn = step-down governor. Jupiter = magnetic commutator / charge flywheel. "
            "Polar vortex = terrestrial axial receiver."
        ),
        "altitude_curve": latitude_altitude_curve(R_f=R_f, A_o=A_o, V_p=V_p),
        "governance_doc_path": str(GOVERNANCE_DOC),
        "governance_yaml_path": str(GOVERNANCE_YAML),
    }


def evaluate_observer(
    phi_deg: float,
    R_f: float | None = None,
    A_o: float | None = None,
    V_p: float | None = None,
) -> dict[str, Any]:
    """Evaluate North Axis Aperture register for a single observer latitude."""
    cfg = load_governance_config()
    defaults = cfg.get("north_axis_aperture", {}).get("defaults", {})
    rf = R_f if R_f is not None else float(defaults.get("R_f", 0.0))
    ao = A_o if A_o is not None else float(defaults.get("A_o", 0.0))
    vp = V_p if V_p is not None else float(defaults.get("V_p", 0.0))
    alpha = north_star_apparent_altitude(phi_deg, rf, ao, vp)
    return {
        "phi_deg": phi_deg,
        "alpha_N_deg": alpha,
        "R_f": rf,
        "A_o": ao,
        "V_p": vp,
        "residual_deg": round(alpha - phi_deg, 4),
        "matches_latitude_rule": math.isclose(alpha, phi_deg, abs_tol=0.01),
    }