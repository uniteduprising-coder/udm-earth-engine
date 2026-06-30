"""
UDM Master Encyclopedia ingestion — T1/T2/T3/T4 provenance layer.
Source: docs/UDM_Master_Encyclopedia.md + config/udm_engine_params.yaml
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from earth.config import ROOT

ENCYCLOPEDIA_MD = ROOT / "docs" / "UDM_Master_Encyclopedia.md"
ENCYCLOPEDIA_YAML = ROOT / "config" / "udm_engine_params.yaml"


def load_sourced_constants() -> dict[str, Any]:
    """T1 empirically sourced constants from encyclopedia params."""
    if not ENCYCLOPEDIA_YAML.exists():
        return {}
    with ENCYCLOPEDIA_YAML.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        "sidereal": raw.get("sidereal", {}),
        "devils_backbone": raw.get("devils_backbone", {}),
        "polar_vortex_sediment": raw.get("polar_vortex_sediment", {}),
    }


def provenance_summary() -> dict[str, Any]:
    """Machine-readable tier summary for UI/engine."""
    return {
        "document": "UDM Master Encyclopedia",
        "compiled": "2026-06-30",
        "tiers": {
            "T1": "Empirically sourced — fixed ground-truth input",
            "T2": "Structural framework — world-model skeleton",
            "T3": "Observational pattern match — render, flag unconfirmed",
            "T4": "Simulation parameter — tunable, not externally validated",
        },
        "validation_corrected": {
            "constants_defined_pct": 100,
            "constants_validated_pct": "partial — 4 T1-adjacent checks",
            "checks_passing": "16/18 defined, 2 pending data (GRACE, jerk correlation run)",
            "blocking_gaps": 0,
        },
        "resolutions_2026_06_30": [
            "L_eff = 3.5242e-4 H (β correct, α arithmetic error)",
            "IMF live feed: NOAA SWPC mag-1-day.json verified",
            "Geomagnetic jerk catalogue updated from published sources",
            "E_break reclassified as T4 generic air breakdown (not basalt lab)",
        ],
        "sourced": load_sourced_constants(),
        "encyclopedia_path": str(ENCYCLOPEDIA_MD),
        "params_path": str(ENCYCLOPEDIA_YAML),
    }


def ingest_encyclopedia() -> dict[str, Any]:
    """Execute encyclopedia ingestion pipeline."""
    from earth.cosmology.imf_hook import fetch_omni2_bz
    from earth.cosmology.jerk_crosscheck import jerk_crosscheck
    from earth.cosmology.km_optimiser import km_sweep
    from earth.cosmology.params import load_params
    from earth.cosmology.validation import run_validation
    from earth.cosmology.engine import get_engine

    engine = get_engine()
    imf = fetch_omni2_bz()
    jerk = jerk_crosscheck(engine)
    km = km_sweep(steps=7)
    validation = run_validation(engine)

    return {
        "ok": True,
        "ingested_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "files": {
            "encyclopedia_md": ENCYCLOPEDIA_MD.exists(),
            "encyclopedia_yaml": ENCYCLOPEDIA_YAML.exists(),
            "geomagnetic_jerks": (ROOT / "validation" / "geomagnetic_jerks.csv").exists(),
        },
        "imf_status": imf.get("status"),
        "imf_Bz_nT": imf.get("Bz_nT"),
        "jerk_report_status": jerk.get("status"),
        "km_optimal": km.get("optimal_Km"),
        "validation_score": f"{validation['passed']}/{validation['total_checks']}",
        "provenance": provenance_summary(),
        "L_eff_H": load_params().get("L_eff"),
    }


def load_jerk_catalogue() -> list[dict[str, str]]:
    path = ROOT / "validation" / "geomagnetic_jerks.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))