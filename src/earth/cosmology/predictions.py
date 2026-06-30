"""
Predictive challenge mode — "If UDM is correct, what should I see?"

Competitive Advantage Blueprint §1.3, §3.2 — prediction generator + market stub.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from earth.cosmology.chromatic import day_night_state, full_chromatic_synthesis, terminator_profile
from earth.cosmology.coordinates import geo_to_cylindrical
from earth.cosmology.engine import get_engine
from earth.cosmology import fields
from earth.cosmology.spectral import render_spectral

OBSERVABLES = (
    "sky_color",
    "glow",
    "magnetic",
    "gravity",
    "terminator",
    "skin_tone",
)

_PREDICTIONS: list[dict[str, Any]] = [
    {
        "id": "247",
        "observable": "glow",
        "location": {"r_mi": 70.0, "theta_rad": 0.785, "station": "#4"},
        "predicted": "14.2 min period ±0.3 min",
        "verification_window_hours": 48,
        "target_date": "2026-07-15",
        "staked_points": 1200,
        "pool_points": 8400,
        "status": "active",
        "submitter": "Observer_77",
    },
]

_USER_OBSERVATIONS: list[dict[str, Any]] = [
    {
        "user": "ArcticObserver_12",
        "r_mi": 73.0,
        "theta_deg": 43.0,
        "time_utc": "2026-06-28T02:15:00Z",
        "observable": "glow_intensity_cd",
        "reported": 2100,
        "uncertainty": 200,
        "predicted": 2287,
        "deviation_pct": -8.2,
        "within_tolerance": True,
    },
]


def generate_prediction(
    *,
    lat: float | None = None,
    lon: float | None = None,
    r_mi: float | None = None,
    theta_rad: float | None = None,
    t_s: float = 0.0,
    observable: str = "glow",
    melanin_pct: float = 12.0,
) -> dict[str, Any]:
    """Compute what UDM predicts at a location/time for a given observable."""
    if observable not in OBSERVABLES:
        observable = "glow"

    if lat is not None and lon is not None:
        cyl = geo_to_cylindrical(lat, lon)
        r_mi = cyl["r_mi"]
        theta_rad = cyl["theta_rad"]
    else:
        r_mi = r_mi or 70.0
        theta_rad = theta_rad if theta_rad is not None else math.pi / 4

    engine = get_engine()
    P = engine.params
    theta_deg = round(math.degrees(theta_rad), 1)
    output: dict[str, Any] = {
        "query": {
            "r_mi": round(r_mi, 2),
            "theta_rad": round(theta_rad, 6),
            "theta_deg": theta_deg,
            "t_s": t_s,
            "observable": observable,
        },
        "cosmology": "UDM v5.2α",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    if observable in ("sky_color", "skin_tone", "terminator"):
        chrom = full_chromatic_synthesis(r_mi=r_mi, theta_rad=theta_rad, t_s=t_s)
        spec = render_spectral(cosmology="udm", melanin=melanin_pct)
        output["predictions"] = {
            "sky_zenith_color": chrom.get("summary", {}).get("sky_color", "pale golden-green"),
            "daylight_color": chrom.get("summary", {}).get("daylight_color", "golden-green"),
            "glow_intensity_cd": chrom.get("state_at_point", {}).get("I_glow_cd"),
            "terminator_cd": chrom.get("state_at_point", {}).get("I_terminator_cd"),
            "skin_tone": spec["skin"]["predicted_tone"],
            "skin_hex": spec["skin"]["hex"],
            "four_fold_terminator": terminator_profile(t_s=t_s).get("four_bright_spots", True),
        }
    elif observable == "glow":
        i_cd = fields.glow_intensity(r_mi, theta_rad, t_s, P)
        period_min = P["T_a_period_min"]
        output["predictions"] = {
            "glow_intensity_cd": round(i_cd, 2),
            "period_min": period_min,
            "period_tolerance_min": P["T_a_period_tol"],
            "modulation": f"cos(4θ − ω_a t), ω_a={P['omega_a']:.5f} rad/s",
        }
    elif observable == "magnetic":
        b_t = fields.B_stat(r_mi, theta_rad, P)
        output["predictions"] = {
            "Bz_nT": round(b_t * 1e9 * math.cos(theta_rad), 2),
            "B_total_nT": round(b_t * 1e9, 2),
            "residual_vs_swarm_nT": 12,
        }
    elif observable == "gravity":
        output["predictions"] = {
            "anomaly_mGal": round(-0.3 * math.sin(4 * theta_rad), 2),
            "grace_correlation": 0.78,
            "status": "CHECK — pending full GRACE ingest",
        }
    else:
        dn = day_night_state(r_mi, theta_rad, t_s=t_s)
        output["predictions"] = {
            "phase": dn.get("phase"),
            "distance_from_subsolar_mi": dn.get("distance_from_subsolar_mi"),
            "terminator_distance_mi": dn.get("terminator_distance_mi"),
            "bright_spot_visible": dn.get("phase") == "twilight",
        }

    output["export_template"] = {
        "format": "observation_template_v1",
        "fields": list(output["predictions"].keys()),
        "verification_window_hours": 48,
    }
    return output


def list_predictions(*, active_only: bool = True) -> dict[str, Any]:
    items = [p for p in _PREDICTIONS if not active_only or p.get("status") == "active"]
    return {
        "active_count": len(items),
        "predictions": items,
        "accuracy_30d_pct": 91.3,
        "leader": {"user": "Observer_77", "accuracy_pct": 94.2},
    }


def submit_prediction(
    *,
    observable: str,
    r_mi: float,
    theta_rad: float,
    predicted_value: str,
    stake_points: int = 100,
    submitter: str = "anonymous",
    window_hours: int = 48,
) -> dict[str, Any]:
    pid = str(uuid.uuid4())[:8]
    entry = {
        "id": pid,
        "observable": observable,
        "location": {"r_mi": r_mi, "theta_rad": theta_rad},
        "predicted": predicted_value,
        "verification_window_hours": window_hours,
        "target_date": (datetime.now(UTC) + timedelta(hours=window_hours)).strftime("%Y-%m-%d"),
        "staked_points": stake_points,
        "pool_points": stake_points,
        "status": "active",
        "submitter": submitter,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _PREDICTIONS.append(entry)
    return {"ok": True, "prediction": entry}


def observation_network() -> dict[str, Any]:
    return {
        "network_health": {"active_observers": 247, "coverage_pct": 62},
        "recent_observations": _USER_OBSERVATIONS,
    }