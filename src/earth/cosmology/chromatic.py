"""
UDM v5.2α — day/night, terminator geometry, and chromatic synthesis.

Derived from the mathematical ledger + luminary_lines.csv + node_table Sun/Moon.
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology import fields
from earth.cosmology.coordinates import cylindrical_to_geo, geo_to_cylindrical
from earth.cosmology.params import load_luminary_spectra, load_node_table, load_params

# Ledger defaults (33 mi / 3000 mi nodes)
SUN_DIAMETER_MI = 33.0
SUN_ALTITUDE_MI = 3000.0
MOON_PHASE_OFFSET_DEG = 11.1
R_DAY_MI = (3000.0, 4000.0)
R_TERM_MI = (3000.0, 3300.0)
TWILIGHT_WIDTH_MI = (50.0, 100.0)
DOMINANT_WAVELENGTH_NM = 557.0
CCT_KELVIN = (4500.0, 5000.0)


def _luminary_node(node_type: str) -> dict[str, Any]:
    for n in load_node_table():
        if n["type"] == node_type:
            return n
    raise KeyError(f"Missing node: {node_type}")


def solar_geometry(P: dict[str, Any] | None = None) -> dict[str, Any]:
    """33-mile Sun at 3,000 mi — angular size and illumination footprint."""
    P = P or load_params()
    sun = _luminary_node("Sun")
    h = sun["z_mi"]
    d = sun["diameter_mi"]
    theta_rad = 2 * math.atan(d / (2 * h))
    theta_deg = math.degrees(theta_rad)
    n0 = fields.n_firmament_real(0, P)
    delta_r_refraction = h * (n0 - 1) / math.sqrt(max(1e-9, 1 - (n0 - 1) ** 2))
    return {
        "diameter_mi": d,
        "altitude_mi": h,
        "angular_diameter_deg": round(theta_deg, 4),
        "observed_solar_deg": 0.53,
        "subsolar_r_mi": sun["r_mi"],
        "subsolar_theta_rad": sun["theta_rad"],
        "illumination_radius_mi": {"min": R_DAY_MI[0], "max": R_DAY_MI[1]},
        "terminator_radius_mi": {"min": R_TERM_MI[0], "max": R_TERM_MI[1]},
        "twilight_zone_mi": {"min": TWILIGHT_WIDTH_MI[0], "max": TWILIGHT_WIDTH_MI[1]},
        "firmament_refraction_extension_mi": round(delta_r_refraction, 2),
        "four_fold_modulation": P["B_mod_amp"],
    }


def lunar_geometry() -> dict[str, Any]:
    """33-mile Moon — resonant aetheric node, +11.1° phase offset."""
    moon = _luminary_node("Moon")
    sun = _luminary_node("Sun")
    return {
        "diameter_mi": moon["diameter_mi"],
        "altitude_mi": moon["z_mi"],
        "phase_offset_deg": MOON_PHASE_OFFSET_DEG,
        "r_mi": moon["r_mi"],
        "theta_rad": moon["theta_rad"],
        "spectrum_matches_sun": True,
        "relative_intensity_vs_sun": 1.0e-4,
        "anti_phase_coupling": True,
        "offset_from_sun_deg": math.degrees(abs(moon["theta_rad"] - sun["theta_rad"])),
    }


def disk_distance(r1: float, t1: float, r2: float, t2: float) -> float:
    """Chord distance on flat disk between cylindrical points."""
    return math.sqrt(r1**2 + r2**2 - 2 * r1 * r2 * math.cos(t1 - t2))


def day_night_state(
    r_mi: float,
    theta_rad: float,
    *,
    t_s: float = 0.0,
    P: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify illumination at (r,θ): day / twilight / night.

    Uses geometric terminator + aetheric glow baseline.
    """
    P = P or load_params()
    sun = _luminary_node("Sun")
    d = disk_distance(r_mi, theta_rad, sun["r_mi"], sun["theta_rad"])
    r_term = 0.5 * (R_TERM_MI[0] + R_TERM_MI[1])
    r_day = 0.5 * (R_DAY_MI[0] + R_DAY_MI[1])
    twilight = 0.5 * (TWILIGHT_WIDTH_MI[0] + TWILIGHT_WIDTH_MI[1])

    if d <= r_term:
        phase = "day"
    elif d <= r_day + twilight:
        phase = "twilight"
    else:
        phase = "night"

    i_glow = fields.glow_intensity(r_mi, theta_rad, t_s, P)
    i_direct = max(0.0, 1.0 - (d - r_term) / max(twilight, 1.0)) if phase != "night" else 0.0
    island_mod = 1.0 + P["B_mod_amp"] * math.cos(4 * theta_rad)
    i_terminator = i_direct * math.exp(-0.01 * d) + i_glow * island_mod

    geo = cylindrical_to_geo(r_mi, theta_rad, R_disk=P["R_disk"])
    return {
        "r_mi": r_mi,
        "theta_rad": theta_rad,
        "lat": geo["lat"],
        "lon": geo["lon"],
        "phase": phase,
        "distance_from_subsolar_mi": round(d, 2),
        "I_glow_cd": round(i_glow, 2),
        "I_terminator_cd": round(i_terminator, 2),
        "island_glow_enhancement": round(island_mod, 4),
        "glow_period_min": P["T_a_period_min"],
    }


def terminator_profile(
    *,
    n_samples: int = 64,
    t_s: float = 0.0,
    P: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Terminator ring with four-fold island modulation + 14.2 min pulsation."""
    P = P or load_params()
    sun = _luminary_node("Sun")
    r_term = 0.5 * (R_TERM_MI[0] + R_TERM_MI[1])
    samples = []
    for i in range(n_samples):
        th = 2 * math.pi * i / n_samples
        r = sun["r_mi"] + r_term * math.cos(th - sun["theta_rad"])
        r = max(0.01, r)
        glow = fields.glow_intensity(r, th, t_s, P)
        mod = 1.0 + P["B_mod_amp"] * math.cos(4 * th)
        samples.append(
            {
                "theta_deg": round(math.degrees(th), 2),
                "r_mi": round(r, 2),
                "I_cd": round(glow * mod, 2),
                "four_fold_factor": round(mod, 4),
            }
        )
    peak = max(samples, key=lambda s: s["I_cd"])
    return {
        "shape": "rounded_square",
        "four_bright_spots": True,
        "pulsation_period_min": P["T_a_period_min"],
        "samples": samples,
        "peak_intercardinal": peak,
    }


def solar_spectrum_analysis() -> dict[str, Any]:
    """Dominant 557 nm green-yellow line → daylight chromaticity."""
    lines = load_luminary_spectra()
    parsed = [
        {
            "wavelength_nm": float(row["wavelength_nm"]),
            "relative_intensity": float(row["relative_intensity"]),
        }
        for row in lines
    ]
    dominant = max(parsed, key=lambda x: x["relative_intensity"])
    return {
        "lines": parsed,
        "dominant_wavelength_nm": dominant["wavelength_nm"],
        "dominant_color": "green-yellow",
        "correlated_color_temperature_K": {"min": CCT_KELVIN[0], "max": CCT_KELVIN[1]},
        "uv_below_391_nm": False,
        "daylight_description": "warm golden-green",
        "sky_description": "pale golden-green near Sun, green-black at zenith",
        "scattering_model": "n''(z)·ρ_a·λ⁻² (not Rayleigh λ⁻⁴)",
    }


def skin_chromatic_prediction(r_mi: float, *, P: dict[str, Any] | None = None) -> dict[str, Any]:
    """Predicted skin undertone from UDM illumination at radial station."""
    P = P or load_params()
    if r_mi < 3000:
        zone, tone = "subsolar", "light-medium golden-olive"
    elif r_mi < 6000:
        zone, tone = "mid_latitude", "fair light golden, greenish undertone"
    else:
        zone, tone = "rim", "very fair, aetheric glow adaptation"
    return {
        "r_mi": r_mi,
        "zone": zone,
        "predicted_tone": tone,
        "undertone": "greenish-golden",
        "melanin_driver": "391 nm violet line (minimal UV-B)",
        "conventional_contrast": "reddish-brown undertone under broad-spectrum Sun",
        "dominant_illuminant_nm": DOMINANT_WAVELENGTH_NM,
    }


def full_chromatic_synthesis(
    *,
    r_mi: float = 70.0,
    theta_rad: float = 0.785,
    t_s: float = 0.0,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Complete day/night/terminator/chromatic report for API."""
    P = load_params()
    if lat is not None and lon is not None:
        cyl = geo_to_cylindrical(lat, lon, R_disk=P["R_disk"])
        r_mi, theta_rad = cyl["r_mi"], cyl["theta_rad"]

    return {
        "version": "5.2α",
        "synthesis": "day_night_terminator_chromatic",
        "solar": solar_geometry(P),
        "lunar": lunar_geometry(),
        "spectrum": solar_spectrum_analysis(),
        "state_at_point": day_night_state(r_mi, theta_rad, t_s=t_s, P=P),
        "skin": skin_chromatic_prediction(r_mi, P=P),
        "terminator": terminator_profile(t_s=t_s, P=P),
        "testable_predictions": [
            "Historical art green-gold skin tone bias",
            "557 nm anomalously strong in quiet night spectra",
            "Skin reflectance inflection near 557 nm",
            "Four-fold dawn enhancement with 14.2 min pulsation",
            "M/L cone sensitivity aligned to 557 nm illuminant",
        ],
        "summary": {
            "daylight_color": "golden-green (557 nm dominant)",
            "sky_color": "pale golden-green",
            "night_illumination": "structured green aetheric glow",
            "moonlight_color": "golden-green (self-luminous node)",
            "skin_undertone": "greenish-golden",
        },
    }