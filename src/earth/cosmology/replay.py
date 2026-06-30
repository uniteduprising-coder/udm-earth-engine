"""
Time-locked historical replay — physics state locked to observation windows.

Competitive Advantage Blueprint §3.1 — 1982 Soviet Polar Expedition anchor.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from earth.cosmology.engine import CosmologyEngine, get_engine
from earth.cosmology.observations import load_1982_stations
from earth.cosmology import fields
from earth.cosmology.validation import validate_1982_glow

EVENTS: dict[str, dict[str, Any]] = {
    "soviet_1982": {
        "id": "soviet_1982",
        "title": "1982 Soviet Polar Expedition",
        "window_start_utc": "1982-03-15T22:00:00Z",
        "window_end_utc": "1982-03-16T06:00:00Z",
        "station": "#4",
        "anchor": {"r_mi": 70.0, "theta_rad": math.pi / 4},
        "observed_period_min": 14.2,
        "observed_period_tol_min": 0.2,
    },
}


def _parse_utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def replay_metadata(event_id: str = "soviet_1982") -> dict[str, Any]:
    ev = EVENTS.get(event_id)
    if not ev:
        return {"error": f"Unknown event: {event_id}"}
    return {**ev, "events_available": list(EVENTS.keys())}


def replay_state(
    event_id: str = "soviet_1982",
    *,
    t_offset_s: float = 0.0,
    engine: CosmologyEngine | None = None,
) -> dict[str, Any]:
    """Model state at a point within a historical observation window."""
    ev = EVENTS.get(event_id)
    if not ev:
        return {"error": f"Unknown event: {event_id}"}

    engine = engine or get_engine()
    P = engine.params
    anchor = ev["anchor"]
    r, th = anchor["r_mi"], anchor["theta_rad"]

    # Map offset into glow period phase
    period_s = P["T_a_period_min"] * 60
    t_sim = t_offset_s % period_s
    omega0 = engine.omega0
    glow = fields.glow_intensity(r, th, t_sim, P)
    sim_period_min = (2 * math.pi / P["omega_a"]) / 60

    stations = load_1982_stations()
    st4 = stations.get("4", [{}])
    obs_glow = st4[0].get("glow_intensity_cd", 920) if st4 else 920

    obs_period = ev["observed_period_min"]
    match_pct = 100 * (1 - abs(sim_period_min - obs_period) / obs_period)

    return {
        "event": ev["title"],
        "event_id": event_id,
        "window": {
            "start": ev["window_start_utc"],
            "end": ev["window_end_utc"],
            "t_offset_s": round(t_offset_s, 2),
        },
        "station": ev["station"],
        "model_state": {
            "Omega0_rad_s": round(omega0, 4),
            "T_em_GW": round(sum(
                fields.T_em_sample(P["r_iso"], fields.island_theta(n), omega0, P) for n in range(4)
            ) / 1e9, 2),
            "I_r_theta_t": {
                "r_mi": r,
                "theta_rad": round(th, 6),
                "I_cd": round(glow, 2),
                "peak_interval_min": round(sim_period_min, 2),
            },
        },
        "comparison": {
            "observed_peaks_min": f"{obs_period} ± {ev['observed_period_tol_min']}",
            "simulated_peaks_min": round(sim_period_min, 2),
            "observed_glow_cd": obs_glow,
            "simulated_glow_cd": round(glow, 2),
            "match_pct": round(match_pct, 1),
        },
        "playback": {
            "playing": False,
            "speed": 1.0,
            "duration_s": (
                _parse_utc(ev["window_end_utc"]) - _parse_utc(ev["window_start_utc"])
            ).total_seconds(),
        },
    }


def replay_tick(
    event_id: str,
    t_offset_s: float,
    *,
    engine: CosmologyEngine | None = None,
) -> dict[str, Any]:
    """Advance replay clock and return updated state."""
    state = replay_state(event_id, t_offset_s=t_offset_s, engine=engine)
    state["playback"]["playing"] = True
    state["playback"]["t_offset_s"] = t_offset_s
    return state