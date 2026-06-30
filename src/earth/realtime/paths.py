from __future__ import annotations

from pathlib import Path

from earth.config import ROOT

MODEL_ROOT = ROOT / "UDM_REALTIME_MODEL"
CONFIG = MODEL_ROOT / "config"
PLATES = MODEL_ROOT / "plates"
DATA = MODEL_ROOT / "data"
DERIVED = MODEL_ROOT / "derived"
RENDERS = MODEL_ROOT / "renders" / "latest"
LOGS = MODEL_ROOT / "logs"


def ensure_dirs() -> None:
    for d in (
        PLATES,
        DATA / "swpc" / "raw",
        DATA / "swpc" / "normalized",
        DATA / "gfz_kp",
        DATA / "noaa_nowcoast" / "satellite",
        DATA / "noaa_nowcoast" / "metadata",
        DATA / "schumann" / "raw",
        DATA / "schumann" / "normalized",
        DERIVED,
        RENDERS,
        LOGS,
    ):
        d.mkdir(parents=True, exist_ok=True)