"""Observation loaders per spec §9.4 and v5.1 addendum."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from earth.config import ROOT

OBS_DIR = ROOT / "observations"


def _csv_path(name: str) -> Path:
    return OBS_DIR / name


def load_1982_stations() -> dict[str, Any]:
    path = _csv_path("soviet_1982_stations.csv")
    stations: dict[str, list] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["station_id"]
            stations.setdefault(sid, []).append(
                {
                    "r_mi": float(row["r_mi"]),
                    "theta_rad": float(row["theta_rad"]),
                    "z_mi": float(row["z_mi"]),
                    "timestamp_utc": row["timestamp_utc"],
                    "glow_intensity_cd": float(row["glow_intensity_cd"]),
                    "uncertainty": float(row["uncertainty"]),
                }
            )
    return stations


def load_schumann_csv() -> dict[str, Any]:
    path = _csv_path("schumann_elf_spectra.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {
        "freq_Hz": [float(r["freq_Hz"]) for r in rows],
        "power": [float(r["power"]) for r in rows],
        "baseline": [float(r.get("baseline", 1.0)) for r in rows],
        "station": [r.get("station", "") for r in rows],
    }


def load_lod_csv() -> dict[str, Any]:
    path = _csv_path("lod_iers_residual.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {
        "mjd": [float(r["mjd"]) for r in rows],
        "lod_ms": [float(r["lod_residual_ms"]) for r in rows],
    }


def load_arctic_mt_anomalies() -> dict[str, Any]:
    path = _csv_path("arctic_mt_anomalies.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {
        "r_mi": [float(r["r_mi"]) for r in rows],
        "theta_rad": [float(r["theta_rad"]) for r in rows],
        "depth_km": [float(r["depth_km"]) for r in rows],
        "conductivity_Sm": [float(r["conductivity_Sm"]) for r in rows],
        "source": [r["source_reference"] for r in rows],
    }


def load_aurora_periodicity() -> dict[str, Any]:
    path = _csv_path("historical_aurora_periodicity.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {
        "period_min": [float(r["period_min"]) for r in rows],
        "amplitude": [float(r["spectral_amplitude"]) for r in rows],
        "expedition": [r["expedition"] for r in rows],
    }


def load_independent_glow_reports() -> dict[str, Any]:
    path = _csv_path("independent_glow_reports.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {"reports": rows}


def load_mercator_geojson() -> dict[str, Any]:
    path = _csv_path("mercator_1569_coastlines.geojson")
    if not path.exists():
        return {"type": "FeatureCollection", "features": [], "status": "queued"}
    return json.loads(path.read_text(encoding="utf-8"))


def list_observation_layers() -> list[dict[str, Any]]:
    return [
        {"key": "soviet_1982", "label": "1982 Soviet Stations", "file": "soviet_1982_stations.csv", "active": True},
        {"key": "mercator_1569", "label": "Mercator 1569 Coastlines", "file": "mercator_1569_coastlines.geojson", "active": True},
        {"key": "fine_1531", "label": "Finé 1531 Landmarks", "file": "fine_1531_landmarks.geojson", "active": True},
        {"key": "swarm_mag", "label": "SWARM Magnetic Anomaly", "file": "swarm_magnetic_anomalies.nc", "active": False},
        {"key": "aurora_hist", "label": "Historical Aurorae (1880–1930)", "file": "historical_aurora_periodicity.csv", "active": False},
        {"key": "glow_reports", "label": "Independent Glow Reports", "file": "independent_glow_reports.csv", "active": False},
        {"key": "mt_conductivity", "label": "MT Conductivity Data", "file": "arctic_mt_anomalies.csv", "active": False},
        {"key": "river_deltas", "label": "Arctic River Deltas", "file": "arctic_river_deltas.geojson", "active": False},
        {"key": "grace_gravity", "label": "GRACE Gravity Anomaly", "file": "grace_gravity_arctic.nc", "active": False},
        {"key": "schumann_elf", "label": "Schumann ELF Spectra", "file": "schumann_elf_spectra.csv", "active": False},
        {"key": "lod_iers", "label": "LOD Residuals (IERS)", "file": "lod_iers_residual.csv", "active": False},
    ]