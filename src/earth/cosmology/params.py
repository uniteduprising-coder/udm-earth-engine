from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from earth.config import ROOT

PARAMS_PATH = ROOT / "config" / "params.yml"
NODE_TABLE_PATH = ROOT / "config" / "node_table.csv"
PUBLIC_PARAMS_PATH = ROOT / "public" / "data" / "cosmology" / "params.json"


_FLOAT_KEYS = {
    "L_f", "r_base", "h_peak", "r_summit", "C_base", "R_disk", "z_roof", "R_earth",
    "r_iso", "a_iso", "sigma_theta", "d_eps_iso", "sigma_iso", "eps0", "mu0",
    "GAMMA_H", "sigma_h", "Q_h", "W_h", "GAMMA_A", "sigma_a", "Q_a", "rho_a0",
    "lambda_abs", "LUM_BETA", "LUM_GAMMA", "C_d", "T_a", "nu_a", "M0", "sigma_eff",
    "sigma_eff_min", "sigma_eff_max", "omega_res", "L_geo", "C_disk", "C_iso",
    "C_total", "L_eff", "B_mod_amp", "kappa", "Omega0_init", "Omega_max", "eta_shear",
    "I_max", "P_target", "P_tolerance", "T_em_divergence_limit", "omega_a", "m_a",
    "T_a_period_min", "T_a_period_tol", "DT_MACRO", "MICRO_DT_MAX", "CFL_LIMIT",
    "r_sink", "r_sink_a", "macro_reduce_threshold", "sigma_disk", "c_s", "E_crit",
}
_INT_KEYS = {"MAX_MACRO", "macro_reduce_steps"}


def _coerce_params(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _FLOAT_KEYS and v is not None:
            out[k] = float(v)
        elif k in _INT_KEYS and v is not None:
            out[k] = int(v)
        else:
            out[k] = v
    return out


def load_params(*, reload: bool = False) -> dict[str, Any]:
    """Hot-load authoritative params.yml."""
    if not PARAMS_PATH.exists():
        raise FileNotFoundError(f"Missing parameter depot: {PARAMS_PATH}")
    with PARAMS_PATH.open(encoding="utf-8") as f:
        return _coerce_params(yaml.safe_load(f))


def save_params(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into params.yml and export JSON for edge CDN."""
    current = load_params()
    current.update(updates)
    PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PARAMS_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    export_params_json(current)
    return current


def export_params_json(params: dict[str, Any] | None = None) -> Path:
    """Bake params for edge worker / static CDN."""
    p = params or load_params()
    payload = {
        "version": "5.1",
        "status": "established",
        "source": "params.yml",
        "params": p,
        "meta": {
            "L_f": p["L_f"],
            "coordinate_basis": "cylindrical (r, theta, z) statute miles",
            "origin": "Rupes Nigra peak",
            "time_zero": "polar midnight",
            "validation_anchor": "1982 Soviet Polar Expedition #122-85",
        },
    }
    PUBLIC_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PARAMS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return PUBLIC_PARAMS_PATH


def load_node_table() -> list[dict[str, Any]]:
    """Parse node_table.csv into records."""
    import csv

    rows: list[dict[str, Any]] = []
    with NODE_TABLE_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "type": row["type"],
                    "x_mi": float(row["x_mi"]),
                    "y_mi": float(row["y_mi"]),
                    "z_mi": float(row["z_mi"]),
                    "diameter_mi": float(row["diameter_mi"]),
                    "phase_deg": float(row["phase_deg"]),
                    "r_mi": (float(row["x_mi"]) ** 2 + float(row["y_mi"]) ** 2) ** 0.5,
                    "theta_rad": __import__("math").atan2(float(row["y_mi"]), float(row["x_mi"])),
                }
            )
    return rows