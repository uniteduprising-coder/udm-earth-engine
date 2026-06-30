"""UDM polar-disk coordinate system derived from master plate."""

from __future__ import annotations

import math
from typing import Any


def load_plate_constants(cfg: dict[str, Any]) -> dict[str, Any]:
    disk = cfg["full_disk_plate"]
    return {
        "cx": float(disk["center_px_initial"][0]),
        "cy": float(disk["center_px_initial"][1]),
        "r_outer": float(disk["outer_radius_px_initial"]),
        "width_px": int(disk["width_px"]),
        "height_px": int(disk["height_px"]),
    }


def plate_to_rho_theta(x_px: float, y_px: float, cx: float, cy: float, r_outer: float) -> tuple[float, float]:
    dx = x_px - cx
    dy = cy - y_px
    rho = math.hypot(dx, dy) / r_outer if r_outer else 0.0
    theta = math.atan2(dx, dy)
    return rho, theta


def rho_theta_to_plate(rho: float, theta: float, cx: float, cy: float, r_outer: float) -> tuple[float, float]:
    r = rho * r_outer
    x_px = cx + r * math.sin(theta)
    y_px = cy - r * math.cos(theta)
    return x_px, y_px


def phi_udm_from_rho(rho: float) -> float:
    return 90.0 - 180.0 * rho


def rho_from_phi_udm(phi_deg: float) -> float:
    return (90.0 - phi_deg) / 180.0


def lonlat_to_provisional_rho_theta(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Provisional overlay mapping — estimated until forensic control points refine mesh."""
    rho = rho_from_phi_udm(lat_deg)
    theta = math.radians(lon_deg)
    return rho, theta


def lonlat_to_plate(
    lon_deg: float,
    lat_deg: float,
    cx: float,
    cy: float,
    r_outer: float,
) -> dict[str, float]:
    rho, theta = lonlat_to_provisional_rho_theta(lon_deg, lat_deg)
    x_px, y_px = rho_theta_to_plate(rho, theta, cx, cy, r_outer)
    return {
        "plate_x": round(x_px, 2),
        "plate_y": round(y_px, 2),
        "rho": round(rho, 6),
        "theta_rad": round(theta, 6),
        "phi_udm_deg": round(phi_udm_from_rho(rho), 4),
        "provisional": True,
    }