"""
UDM v5.0 coordinate basis: cylindrical (r, θ, z) in statute miles.

Origin at Rupes Nigra peak. Geographic bijection per spec §9.1:
  colatitude = (π/2) · (r / R_disk)
  longitude  = θ
"""

from __future__ import annotations

import math
from typing import Any

STATUTE_MI_TO_KM = 1.609344
FRENCH_MI_TO_STATUTE = 2.428


def geo_to_cylindrical(
    lat: float,
    lon: float,
    *,
    z_mi: float = 0.0,
    R_disk: float = 12500.0,
) -> dict[str, float]:
    """Geographic WGS84 → UDM cylindrical (statute miles, radians)."""
    colat_rad = math.radians(90.0 - lat)
    r_mi = (2.0 * colat_rad / math.pi) * R_disk
    theta_rad = math.radians(lon)
    return {
        "r_mi": round(r_mi, 6),
        "theta_rad": round(theta_rad, 8),
        "z_mi": round(z_mi, 6),
        "colatitude_deg": round(math.degrees(colat_rad), 6),
    }


def cylindrical_to_geo(
    r_mi: float,
    theta_rad: float,
    *,
    R_disk: float = 12500.0,
) -> dict[str, float]:
    """UDM cylindrical → geographic WGS84."""
    colat_rad = (math.pi / 2.0) * (r_mi / R_disk)
    lat = 90.0 - math.degrees(colat_rad)
    lon = math.degrees(theta_rad)
    while lon > 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0
    return {"lat": round(lat, 6), "lon": round(lon, 6)}


def statute_to_french_mi(mi: float) -> float:
    return mi / FRENCH_MI_TO_STATUTE


def french_to_statute_mi(lf: float) -> float:
    return lf * FRENCH_MI_TO_STATUTE


def project_site(
    lat: float,
    lon: float,
    *,
    R_disk: float = 12500.0,
    mode: str = "udm_v5",
) -> dict[str, Any]:
    """
    Full projection record for map rendering.

    udm_v5: cylindrical bijection → lat_udm/lon_udm for Leaflet display.
    udm_flat: legacy Frame-U winding projection (imported when needed).
    wgs84: passthrough.
    """
    if mode == "wgs84":
        return {
            "mode": mode,
            "lat_raw": lat,
            "lon_raw": lon,
            "lat_udm": lat,
            "lon_udm": lon,
            "r_mi": geo_to_cylindrical(lat, lon, R_disk=R_disk)["r_mi"],
            "theta_rad": geo_to_cylindrical(lat, lon, R_disk=R_disk)["theta_rad"],
        }

    cyl = geo_to_cylindrical(lat, lon, R_disk=R_disk)
    geo = cylindrical_to_geo(cyl["r_mi"], cyl["theta_rad"], R_disk=R_disk)

    if mode == "udm_v5":
        return {
            "mode": mode,
            "lat_raw": lat,
            "lon_raw": lon,
            "lat_udm": geo["lat"],
            "lon_udm": geo["lon"],
            **cyl,
            "r_french_mi": round(statute_to_french_mi(cyl["r_mi"]), 6),
            "x_mi": round(cyl["r_mi"] * math.cos(cyl["theta_rad"]), 6),
            "y_mi": round(cyl["r_mi"] * math.sin(cyl["theta_rad"]), 6),
        }

    from earth.projection.udm import project_flat

    legacy = project_flat(lat, lon, mode="udm_flat")
    legacy["mode"] = mode
    legacy.update(cyl)
    return legacy