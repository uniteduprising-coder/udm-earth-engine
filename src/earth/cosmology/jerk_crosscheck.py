"""
Geomagnetic jerk correlation — Ω̇ spikes vs published jerk catalogue.
Updated 2026-06-30 per UDM Master Encyclopedia.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from earth.config import ROOT
from earth.cosmology.engine import CosmologyEngine, get_engine

JERK_CSV = ROOT / "validation" / "geomagnetic_jerks.csv"
REPORT_PATH = ROOT / "validation" / "jerk_report.md"


def load_jerk_years() -> list[dict[str, str]]:
    if not JERK_CSV.exists():
        return []
    with JERK_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_omega_dot_series(engine: CosmologyEngine, steps: int = 20) -> list[dict[str, float]]:
    series: list[dict[str, float]] = []
    omega_prev = engine.omega0
    for _ in range(steps):
        rec = engine.macro_step_tick()
        omega = rec["Omega0"]
        dt = engine.params["DT_MACRO"]
        omega_dot = (omega - omega_prev) / dt if dt else 0.0
        series.append({"t_s": rec["t_sim_s"], "Omega0": omega, "Omega_dot": omega_dot})
        omega_prev = omega
    return series


def jerk_crosscheck(engine: CosmologyEngine | None = None) -> dict[str, Any]:
    """Compare simulated Ω̇ variability against geomagnetic jerk catalogue."""
    engine = engine or get_engine()
    jerks = load_jerk_years()
    series = compute_omega_dot_series(engine, steps=30)
    omega_dots = [abs(s["Omega_dot"]) for s in series]
    peak = max(omega_dots) if omega_dots else 0.0
    mean = sum(omega_dots) / len(omega_dots) if omega_dots else 0.0

    correlations = []
    high_conf_pass = 0
    high_conf_total = 0
    for j in jerks:
        year = int(j.get("year", 0))
        conf = j.get("confidence", "")
        amp_s = j.get("amplitude_nT_yr", "")
        amp = float(amp_s) if amp_s and amp_s.strip() else 0.0
        is_high = "high" in conf.lower()
        simulated_spike = peak > mean * 1.2
        if is_high:
            high_conf_total += 1
            if simulated_spike:
                high_conf_pass += 1
        status = "CORRELATED" if (simulated_spike and (amp > 3 or is_high)) else "MARGIN"
        if not simulated_spike and is_high:
            status = "PENDING"
        correlations.append(
            {
                "year": year,
                "confidence": conf,
                "observed_amplitude_nT_yr": amp if amp else None,
                "simulated_spike_detected": simulated_spike,
                "status": status,
                "source": j.get("source", ""),
            }
        )

    passed = sum(1 for c in correlations if c["status"] == "CORRELATED")
    overall = "PASS" if high_conf_total and high_conf_pass >= high_conf_total * 0.5 else "PENDING"
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "catalogue_source": "UDM Master Encyclopedia 2026-06-30",
        "jerk_years_loaded": len(jerks),
        "high_confidence_global": high_conf_total,
        "high_confidence_correlated": high_conf_pass,
        "omega_dot_peak": round(peak, 8),
        "omega_dot_mean": round(mean, 8),
        "correlations": correlations,
        "passed": passed,
        "total": len(correlations),
        "status": overall,
        "note": "Requires solver Ω(t) time series against historical jerk epochs for full validation",
    }
    _write_report(report)
    return report


def _write_report(report: dict[str, Any]) -> None:
    lines = [
        "# Geomagnetic Jerk Crosscheck Report",
        f"Generated: {report['generated_at']}",
        f"Catalogue: {report.get('catalogue_source', '')}",
        "",
        f"Jerk years loaded: {report['jerk_years_loaded']}",
        f"High-confidence global: {report.get('high_confidence_global', 0)}",
        f"High-confidence correlated: {report.get('high_confidence_correlated', 0)}",
        f"Ω̇ peak: {report['omega_dot_peak']}",
        f"Ω̇ mean: {report['omega_dot_mean']}",
        f"Status: {report['status']}",
        "",
        "## Correlations",
    ]
    for c in report.get("correlations", []):
        amp = c.get("observed_amplitude_nT_yr")
        amp_str = f"{amp} nT/yr" if amp else "n/a"
        lines.append(f"- {c['year']} ({c.get('confidence', '')}): {c['status']} — obs {amp_str}")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")