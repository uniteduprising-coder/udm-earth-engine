"""
Physics-based spectral rendering pipeline (380–780 nm, 5 nm bins).

Competitive Advantage Blueprint §2.1 — LMS cone integration → display RGB.
"""

from __future__ import annotations

import math
from typing import Any

from earth.cosmology.params import load_luminary_spectra, load_params

WL_MIN = 380.0
WL_MAX = 780.0
WL_STEP = 5.0
N_BINS = int((WL_MAX - WL_MIN) / WL_STEP) + 1  # 81


def _wavelengths() -> list[float]:
    return [WL_MIN + i * WL_STEP for i in range(N_BINS)]


def _gaussian(lam: float, center: float, sigma: float = 18.0) -> float:
    return math.exp(-0.5 * ((lam - center) / sigma) ** 2)


def _cie_lms(lam: float) -> tuple[float, float, float]:
    """Approximate CIE 1931 2° LMS fundamentals (normalized)."""
    l = _gaussian(lam, 570, 45) * 1.0 + _gaussian(lam, 450, 30) * 0.15
    m = _gaussian(lam, 540, 40) * 0.9 + _gaussian(lam, 480, 25) * 0.2
    s = _gaussian(lam, 440, 30) * 1.0
    return l, m, s


def udm_illuminant_spectrum(*, dominant_nm: float = 557.0) -> list[dict[str, float]]:
    """UDM Sun spectrum — 557 nm dominant with ledger line contributions."""
    lines = load_luminary_spectra()
    spectrum: list[dict[str, float]] = []
    for lam in _wavelengths():
        intensity = _gaussian(lam, dominant_nm, 22) * 1.0
        for line in lines:
            wl = float(line.get("wavelength_nm", 0))
            rel = float(line.get("relative_intensity", 0))
            intensity += rel * _gaussian(lam, wl, 8)
        spectrum.append({"wavelength_nm": lam, "radiance": round(intensity, 6)})
    peak = max(s["radiance"] for s in spectrum)
    if peak > 0:
        for s in spectrum:
            s["radiance"] = round(s["radiance"] / peak, 6)
    return spectrum


def copernican_illuminant_spectrum() -> list[dict[str, float]]:
    """Approximate D65 daylight for comparison."""
    spectrum: list[dict[str, float]] = []
    for lam in _wavelengths():
        # Simplified Planck-like + blue sky contribution
        t = 6500.0
        c1 = 3.74183e-16
        c2 = 1.4388e-2
        lam_m = lam * 1e-9
        planck = c1 / (lam_m**5 * (math.exp(c2 / (lam_m * t)) - 1.0)) if lam_m > 0 else 0
        intensity = planck * 1e12 + _gaussian(lam, 480, 60) * 0.3
        spectrum.append({"wavelength_nm": lam, "radiance": round(intensity, 6)})
    peak = max(s["radiance"] for s in spectrum)
    for s in spectrum:
        s["radiance"] = round(s["radiance"] / peak, 6)
    return spectrum


def _skin_reflectance(lam: float, melanin: float, hemoglobin: float) -> float:
    """Simplified melanin + hemoglobin spectral reflectance."""
    mel = melanin / 100.0
    hemo = hemoglobin / 100.0
    base = 0.35 + 0.45 * (1 - mel)
    mel_abs = _gaussian(lam, 400, 40) * mel * 0.6
    hemo_abs = _gaussian(lam, 540, 25) * hemo * 0.4 + _gaussian(lam, 420, 20) * hemo * 0.3
    return max(0.05, base - mel_abs - hemo_abs)


def integrate_lms(
    illuminant: list[dict[str, float]],
    *,
    melanin: float = 12.0,
    hemoglobin: float = 85.0,
    aether_glow_factor: float = 1.0,
) -> dict[str, Any]:
    """Integrate spectral radiance × reflectance × LMS fundamentals."""
    lms = [0.0, 0.0, 0.0]
    for band in illuminant:
        lam = band["wavelength_nm"]
        i = band["radiance"] * aether_glow_factor
        r = _skin_reflectance(lam, melanin, hemoglobin)
        cl, cm, cs = _cie_lms(lam)
        lms[0] += i * r * cl
        lms[1] += i * r * cm
        lms[2] += i * r * cs
    return {"lms": [round(v, 6) for v in lms], "melanin_pct": melanin, "hemoglobin_pct": hemoglobin}


def lms_to_srgb(l: float, m: float, s: float) -> tuple[float, float, float]:
    """Bradford-adapted LMS → linear sRGB (simplified matrix)."""
    r = 4.4679 * l - 1.5363 * m - 0.0046 * s
    g = -1.2186 * l + 2.8139 * m + 0.0025 * s
    b = 0.0497 * l - 0.0778 * m + 0.9443 * s
    return r, g, b


def tone_map(rgb: tuple[float, float, float], exposure: float = 1.2) -> tuple[int, int, int]:
    """HDR → SDR Reinhard tone mapping."""
    out = []
    for c in rgb:
        v = c * exposure
        mapped = v / (1.0 + v)
        out.append(max(0, min(255, int(mapped * 255))))
    return out[0], out[1], out[2]


def render_spectral(
    *,
    cosmology: str = "udm",
    melanin: float = 12.0,
    hemoglobin: float = 85.0,
    aether_glow_factor: float = 1.0,
) -> dict[str, Any]:
    """Full spectral render pass for skin + sky preview."""
    if cosmology == "copernican":
        illum = copernican_illuminant_spectrum()
        label = "D65 daylight"
    else:
        illum = udm_illuminant_spectrum()
        label = "UDM 557 nm dominant"

    skin_lms = integrate_lms(illum, melanin=melanin, hemoglobin=hemoglobin, aether_glow_factor=aether_glow_factor)
    sky_lms = integrate_lms(illum, melanin=0, hemoglobin=0, aether_glow_factor=aether_glow_factor * 1.5)
    sl, sm, ss = skin_lms["lms"]
    kl, km, ks = sky_lms["lms"]
    skin_rgb = tone_map(lms_to_srgb(sl, sm, ss))
    sky_rgb = tone_map(lms_to_srgb(kl, km, ks))

    dominant_nm = 557.0 if cosmology == "udm" else 550.0
    return {
        "pipeline": "spectral",
        "bins": N_BINS,
        "wavelength_range_nm": [WL_MIN, WL_MAX],
        "bin_step_nm": WL_STEP,
        "cosmology": cosmology,
        "illuminant_label": label,
        "dominant_wavelength_nm": dominant_nm,
        "illuminant": illum[::4],  # subsample for API payload
        "skin": {
            "lms": skin_lms["lms"],
            "rgb": list(skin_rgb),
            "hex": f"#{skin_rgb[0]:02x}{skin_rgb[1]:02x}{skin_rgb[2]:02x}",
            "predicted_tone": "golden-olive" if cosmology == "udm" else "neutral-warm",
        },
        "sky_zenith": {
            "lms": sky_lms["lms"],
            "rgb": list(sky_rgb),
            "hex": f"#{sky_rgb[0]:02x}{sky_rgb[1]:02x}{sky_rgb[2]:02x}",
            "label": "green-gold" if cosmology == "udm" else "blue-white",
        },
        "params": load_params() if cosmology == "udm" else {},
    }