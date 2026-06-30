"""Inverse-warp external rasters onto UDM plate (overlay only)."""

from __future__ import annotations

import io
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from earth.realtime.coordinates import lonlat_to_provisional_rho_theta, rho_theta_to_plate
from earth.realtime.paths import DATA, DERIVED, RENDERS

GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
GIBS_LAYER = "VIIRS_SNPP_CorrectedReflectance_TrueColor"


async def fetch_gibs_truecolor(width: int = 2048, height: int = 1024) -> dict[str, Any]:
    """Fetch global equirectangular true-color from NASA GIBS WMS."""
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "LAYERS": GIBS_LAYER,
        "CRS": "EPSG:4326",
        "BBOX": "-180,-90,180,90",
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "FORMAT": "image/png",
        "STYLES": "",
    }
    out_dir = DATA / "nasa_gibs" / "viirs"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(GIBS_WMS, params=params)
            if r.status_code != 200 or not r.content.startswith(b"\x89PNG"):
                return {"ok": False, "status": r.status_code, "error": "not_png"}
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            raw_path = out_dir / f"truecolor_{ts}.png"
            raw_path.write_bytes(r.content)
            meta = {
                "source_name": "nasa_gibs",
                "source_url": GIBS_WMS,
                "layer": GIBS_LAYER,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "projection": "EPSG:4326",
                "bbox": [-180, -90, 180, 90],
                "width": width,
                "height": height,
                "raw_path": str(raw_path),
                "geometry_policy": "overlay_only",
            }
            (out_dir / "latest_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            return {"ok": True, "path": str(raw_path), "metadata": meta}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _lonlat_to_source_px(lon_deg: float, lat_deg: float, sw: int, sh: int) -> tuple[int, int]:
    u = (lon_deg + 180.0) / 360.0
    v = (90.0 - lat_deg) / 180.0
    x = int(max(0, min(sw - 1, u * (sw - 1))))
    y = int(max(0, min(sh - 1, v * (sh - 1))))
    return x, y


def inverse_warp_to_plate(
    source_path: Path,
    disk: dict[str, Any],
    out_path: Path,
    *,
    opacity: float = 0.72,
) -> dict[str, Any]:
    """Inverse-warp equirectangular source onto UDM plate pixels."""
    from PIL import Image

    cx = float(disk.get("center_px_refined", disk["center_px_initial"])[0])
    cy = float(disk.get("center_px_refined", disk["center_px_initial"])[1])
    r_outer = float(disk.get("outer_radius_px_refined", disk["outer_radius_px_initial"]))
    iw = int(disk.get("width_px", 2048))
    ih = int(disk.get("height_px", 2044))

    src = Image.open(source_path).convert("RGBA")
    sw, sh = src.size
    src_px = src.load()

    overlay = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    dst_px = overlay.load()
    samples = 0

    y0 = max(0, int(cy - r_outer))
    y1 = min(ih, int(cy + r_outer) + 1)
    x0 = max(0, int(cx - r_outer))
    x1 = min(iw, int(cx + r_outer) + 1)

    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = x - cx
            dy = cy - y
            rho = math.hypot(dx, dy) / r_outer
            if rho > 1.0:
                continue
            theta = math.atan2(dx, dy)
            phi = 90.0 - 180.0 * rho
            lon = math.degrees(theta)
            sx, sy = _lonlat_to_source_px(lon, phi, sw, sh)
            sr, sg, sb, sa = src_px[sx, sy]
            a = int(sa * opacity)
            if a > 8:
                dst_px[x, y] = (sr, sg, sb, a)
                samples += 1

    overlay.save(out_path)
    return {
        "ok": True,
        "path": str(out_path),
        "samples": samples,
        "opacity": opacity,
        "provisional_mesh": True,
    }


def composite_layers(
    base_path: Path,
    overlay_path: Path | None,
    disk: dict[str, Any],
    out_path: Path,
) -> dict[str, Any]:
    """Blend base plate + atmospheric overlay + equator ring hint."""
    from PIL import Image, ImageDraw

    base = Image.open(base_path).convert("RGBA")
    if overlay_path and overlay_path.exists():
        ov = Image.open(overlay_path).convert("RGBA")
        base = Image.alpha_composite(base, ov)

    cx = float(disk.get("center_px_refined", disk["center_px_initial"])[0])
    cy = float(disk.get("center_px_refined", disk["center_px_initial"])[1])
    r_eq = float(disk.get("outer_radius_px_refined", disk["outer_radius_px_initial"])) * 0.5

    draw = ImageDraw.Draw(base)
    draw.ellipse(
        [cx - r_eq, cy - r_eq, cx + r_eq, cy + r_eq],
        outline=(0, 255, 120, 90),
        width=2,
    )
    draw.ellipse(
        [cx - 6, cy - 6, cx + 6, cy + 6],
        fill=(255, 255, 255, 200),
        outline=(0, 200, 255, 220),
    )

    base.convert("RGB").save(out_path, quality=92)
    return {"ok": True, "path": str(out_path)}


async def warp_live_layers(disk: dict[str, Any], plate_cfg: dict[str, Any]) -> dict[str, Any]:
    """Fetch GIBS and warp onto plate; build composite PNG."""
    from earth.realtime.paths import PLATES

    RENDERS.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"layers": {}}

    gibs = await fetch_gibs_truecolor()
    result["gibs_fetch"] = gibs
    if not gibs.get("ok"):
        return result

    warp_path = RENDERS / "udm_live_geocolor.png"
    warp_meta = inverse_warp_to_plate(Path(gibs["path"]), disk, warp_path)
    result["layers"]["geocolor"] = warp_meta

    base = PLATES / plate_cfg["full_disk_plate"]["file"]
    composite_path = RENDERS / "udm_composite.png"
    if base.exists():
        comp = composite_layers(base, warp_path if warp_meta.get("ok") else None, disk, composite_path)
        result["layers"]["composite"] = comp

    # Copy warp mesh path reference
    mesh_path = DERIVED / "udm_noaa_warp_mesh.json"
    if mesh_path.exists():
        result["warp_mesh"] = str(mesh_path)

    return result