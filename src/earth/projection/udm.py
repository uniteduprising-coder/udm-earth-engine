"""
UDM Frame-T flat projection for map rendering.

Maps WGS84 measurement addresses (Frame M) to UDM flat render coordinates (Frame U).
Canonical operators: W(φ), Bloch node, stator phase, κ coupling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

PHI_WIND_DEG = 70.55
PHI_NODE_DEG = -19.45
ALPHA_ANTI_H = 16.9
KAPPA_COUPLING = 0.0514
A_CALIB_MMHG = 0.1699
EARTH_RADIUS_KM = 6371.0

ProjectionMode = Literal["udm_v5", "udm_flat", "wgs84"]


@dataclass(frozen=True)
class UDMConstants:
    phi_wind_deg: float = PHI_WIND_DEG
    phi_node_deg: float = PHI_NODE_DEG
    alpha_anti_h: float = ALPHA_ANTI_H
    kappa: float = KAPPA_COUPLING


def winding_function(phi_deg: float) -> float:
    """W(φ) = cos(φ − 70.55°)."""
    return math.cos(math.radians(phi_deg - PHI_WIND_DEG))


def amplitude_loading(phi_deg: float) -> float:
    """A(φ) = 0.1699 · W(φ) mm Hg."""
    return A_CALIB_MMHG * winding_function(phi_deg)


def stator_phase_modulation(lst_hours: float) -> float:
    """cos(LST − α_anti), α_anti = 16.9h."""
    return math.cos(2.0 * math.pi * (lst_hours - ALPHA_ANTI_H) / 24.0)


def master_relation(phi_deg: float, lst_hours: float, *, baseline: float = 0.0, gain: float = 1.0) -> float:
    """Y = B + G · κ · W(φ) · cos(LST − α_anti)."""
    return baseline + gain * KAPPA_COUPLING * winding_function(phi_deg) * stator_phase_modulation(lst_hours)


def project_flat(
    lat: float,
    lon: float,
    *,
    lst_hours: float = 12.0,
    mode: ProjectionMode = "udm_v5",
) -> dict:
    """
    Project lat/lon to UDM coordinates for rendering.

    udm_v5: cylindrical bijection per Cosmology Engine v5.0 (§9.1).
    udm_flat: legacy Frame-U winding projection.
    """
    if mode == "udm_v5":
        from earth.cosmology.coordinates import project_site

        rec = project_site(lat, lon, mode="udm_v5")
        x_km = rec["x_mi"] * 1.609344
        y_km = rec["y_mi"] * 1.609344
        return {
            "mode": mode,
            "lat_raw": lat,
            "lon_raw": lon,
            "lat_udm": rec["lat_udm"],
            "lon_udm": rec["lon_udm"],
            "r_mi": rec["r_mi"],
            "theta_rad": rec["theta_rad"],
            "x_km": round(x_km, 4),
            "y_km": round(y_km, 4),
            "L_f": 2.428,
            "lst_hours": lst_hours,
        }

    if mode == "wgs84":
        x_km = lon * (math.pi / 180.0) * EARTH_RADIUS_KM * math.cos(math.radians(lat))
        y_km = lat * (math.pi / 180.0) * EARTH_RADIUS_KM
        return {
            "mode": mode,
            "lat_raw": lat,
            "lon_raw": lon,
            "lat_udm": lat,
            "lon_udm": lon,
            "x_km": round(x_km, 4),
            "y_km": round(y_km, 4),
            "W": winding_function(lat),
            "A_mmhg": amplitude_loading(lat),
            "Y": master_relation(lat, lst_hours),
        }

    w = winding_function(lat)
    phase = stator_phase_modulation(lst_hours)
    node_pull = (PHI_NODE_DEG - lat) * abs(w) * 0.08
    lat_udm = lat + node_pull
    lon_scale = abs(w) * (0.92 + 0.08 * phase)
    lon_udm = lon * lon_scale

    x_km = lon_udm * (math.pi / 180.0) * EARTH_RADIUS_KM * math.cos(math.radians(lat_udm))
    y_km = lat_udm * (math.pi / 180.0) * EARTH_RADIUS_KM

    return {
        "mode": mode,
        "lat_raw": lat,
        "lon_raw": lon,
        "lat_udm": round(lat_udm, 6),
        "lon_udm": round(lon_udm, 6),
        "x_km": round(x_km, 4),
        "y_km": round(y_km, 4),
        "W": round(w, 6),
        "A_mmhg": round(amplitude_loading(lat), 6),
        "Y": round(master_relation(lat, lst_hours), 6),
        "lst_hours": lst_hours,
        "stator_phase": round(phase, 6),
    }


def project_point_feature(
    props: dict,
    *,
    lat_key: str = "lat",
    lon_key: str = "lon",
    lst_hours: float = 12.0,
    mode: ProjectionMode = "udm_flat",
) -> dict:
    """Attach UDM projection fields to a site record."""
    lat = float(props[lat_key])
    lon = float(props[lon_key])
    proj = project_flat(lat, lon, lst_hours=lst_hours, mode=mode)
    return {**props, "udm": proj}


def feature_collection(
    sites: list[dict],
    *,
    lst_hours: float = 12.0,
    mode: ProjectionMode = "udm_flat",
    layer_id: str = "",
) -> dict:
    """Build GeoJSON FeatureCollection with UDM-corrected coordinates."""
    features = []
    for site in sites:
        lat = site.get("lat")
        lon = site.get("lon")
        if lat is None or lon is None:
            continue
        proj = project_flat(float(lat), float(lon), lst_hours=lst_hours, mode=mode)
        coord = [proj["lon_udm"], proj["lat_udm"]] if mode == "udm_flat" else [float(lon), float(lat)]
        features.append(
            {
                "type": "Feature",
                "id": site.get("id") or site.get("site_id"),
                "geometry": {"type": "Point", "coordinates": coord},
                "properties": {
                    **{k: v for k, v in site.items() if k not in ("lat", "lon")},
                    "lat_raw": lat,
                    "lon_raw": lon,
                    "layer_id": layer_id or site.get("layer_id", ""),
                    "udm": proj,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features, "layer_id": layer_id, "projection": mode}