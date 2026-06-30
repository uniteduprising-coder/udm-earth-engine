from __future__ import annotations

import math
from datetime import UTC, datetime

from earth.handlers.base import FeedHandler
from earth.projection.udm import project_flat


def _julian_day(dt: datetime) -> float:
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = int(y / 100)
    b = 2 - a + int(a / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _sun_position(dt: datetime) -> dict:
    jd = _julian_day(dt)
    n = jd - 2451545.0
    L = math.radians((280.46 + 0.9856474 * n) % 360)
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = L + math.radians(1.915 * math.sin(g) + 0.02 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    ra_deg = math.degrees(ra) % 360
    dec_deg = math.degrees(dec)
    subsolar_lon = (ra_deg - (dt.hour + dt.minute / 60) * 15 + 180) % 360 - 180
    subsolar_lat = dec_deg
    return {
        "subsolar_lat": round(subsolar_lat, 4),
        "subsolar_lon": round(subsolar_lon, 4),
        "declination_deg": round(dec_deg, 4),
        "right_ascension_deg": round(ra_deg, 4),
    }


def _moon_position(dt: datetime) -> dict:
    jd = _julian_day(dt)
    n = jd - 2451545.0
    lam = math.radians((218.316 + 13.176396 * n) % 360)
    M = math.radians((134.963 + 13.064993 * n) % 360)
    F = math.radians((93.272 + 13.229350 * n) % 360)
    lon = lam + math.radians(6.289 * math.sin(M))
    lat = math.radians(5.128 * math.sin(F))
    phase = (1 - math.cos(M)) / 2
    return {
        "ecliptic_lon_deg": round(math.degrees(lon) % 360, 4),
        "ecliptic_lat_deg": round(math.degrees(lat), 4),
        "illumination": round(phase, 4),
        "approx_subsolar_lat": round(math.degrees(lat), 4),
        "approx_subsolar_lon": round((math.degrees(lon) - 180) % 360 - 180, 4),
    }


class EphemerisHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        now = datetime.now(UTC)
        sun = _sun_position(now)
        moon = _moon_position(now)
        lst_hours = (now.hour + now.minute / 60 + now.second / 3600) % 24
        sun_udm = project_flat(sun["subsolar_lat"], sun["subsolar_lon"], lst_hours=lst_hours)
        moon_udm = project_flat(
            moon.get("approx_subsolar_lat", 0),
            moon.get("approx_subsolar_lon", 0),
            lst_hours=lst_hours,
        )
        return self.cache(
            feed["id"],
            {
                "timestamp": now.isoformat(),
                "lst_hours_utc": round(lst_hours, 4),
                "sun": {**sun, "udm": sun_udm},
                "moon": {**moon, "udm": moon_udm},
            },
        )