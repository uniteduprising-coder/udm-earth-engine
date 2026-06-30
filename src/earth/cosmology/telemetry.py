"""
WebSocket telemetry encoder — binary frame stream from solver to renderer.

Competitive Advantage Blueprint §4.2.
"""

from __future__ import annotations

import struct
from typing import Any

FRAME_PHYSICS = 0x01
FRAME_VALIDATION = 0x05


def pack_physics_frame(timestamp: float, state: dict[str, Any]) -> bytes:
    """Frame type 0x01 — physics state (Ω₀, T_em, P, etc.)."""
    header = struct.pack("<dii", timestamp, FRAME_PHYSICS, 32)
    body = struct.pack(
        "<ddddi",
        float(state.get("Omega0", 0)),
        float(state.get("P_GW", 0)),
        float(state.get("t_sim_s", 0)),
        float(state.get("fields_at_anchor", {}).get("I_cd", 0)),
        int(state.get("macro_step", 0)),
    )
    return header + body


def pack_validation_frame(timestamp: float, report: dict[str, Any]) -> bytes:
    """Frame type 0x05 — validation check summary."""
    passed = int(report.get("passed", 0))
    total = int(report.get("total_checks", 18))
    score = passed / total if total else 0.0
    header = struct.pack("<dii", timestamp, FRAME_VALIDATION, 12)
    body = struct.pack("<iid", passed, total, score)
    return header + body


def telemetry_json_frame(
    timestamp: float,
    *,
    state: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """JSON fallback for browsers without binary decode."""
    out: dict[str, Any] = {"timestamp": timestamp, "frames": []}
    if state:
        out["frames"].append({"type": FRAME_PHYSICS, "physics": state})
    if validation:
        out["frames"].append(
            {
                "type": FRAME_VALIDATION,
                "passed": validation.get("passed"),
                "total": validation.get("total_checks"),
                "score_pct": round(
                    100 * validation.get("passed", 0) / max(1, validation.get("total_checks", 18)),
                    1,
                ),
                "checks": validation.get("checks", [])[:6],
            }
        )
    return out