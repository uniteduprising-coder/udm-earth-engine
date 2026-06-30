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
    "L_f", "r_base", "h_peak", "r_summit", "C_base", "R_disk", "z_max", "z_T", "z_roof", "R_earth",
    "r_iso", "a_iso", "d_iso", "island_depth", "sigma_theta", "d_eps_iso", "eps_bump", "sigma_iso",
    "sigma_iso_depth_scale", "Z_g", "eps0", "mu0", "eps_disk_factor", "E_crit",
    "GAMMA_H", "Gamma_h", "sigma_h", "Q_h", "W_h", "GAMMA_B", "Gamma_b", "Q_B", "Q_b", "W_b",
    "GAMMA_A", "Gamma_a", "sigma_a", "Q_a", "rho_a0", "rho0", "lambda_abs", "LUM_BETA", "LUM_GAMMA",
    "C_d", "T_a", "R_gas", "nu_a", "nu_h", "nu_b", "nu_a_below", "K_m", "Km", "Km_below",
    "Km_sweep_range", "Km_rmse_target", "Q_visc", "M0", "B0", "B_mod_amp", "sigma_eff",
    "sigma_eff_min", "sigma_eff_max", "omega_res", "f_res", "L_geo", "C_disk", "C_iso",
    "C_total", "L_eff", "E_break", "Omega0_init", "Omega0", "Omega_max", "Omega_abort",
    "kappa", "I_rot", "eta_shear", "I_max", "P_target", "P_tolerance", "T_em_divergence_limit",
    "omega_a", "omega_a_below", "phase_shift_below", "m_a", "m_a_below",
    "T_a_period_min", "T_a_period_tol", "n_real_amp", "n_real0", "n_real_scale", "n_imag0",
    "n_imag_scale", "n_H_abs", "schumann_Q", "schumann_df_Hz", "rho_below_factor",
    "glow_below_scale", "imf_scale", "imf_lowpass_hours", "imf_fetch_interval",
    "void_rho", "void_sigma", "void_n", "void_opacity",
    "DT_MACRO", "MICRO_DT_MAX", "CFL_LIMIT", "CFL_max", "r_sink", "r_sink_a",
    "macro_reduce_threshold", "sigma_disk", "c_s", "spectral_start_nm", "spectral_end_nm",
    "spectral_step_nm", "cone_L_peak", "cone_M_peak", "cone_S_peak",
}
_INT_KEYS = {
    "MAX_MACRO", "macro_reduce_steps", "theta_global_N", "theta_refine_factor",
    "multigrid_levels", "amr_levels", "amr_patch_size", "spectral_bins",
}
_BOOL_KEYS = {
    "imf_coupling_enabled", "gpu_amr_enabled", "amr_enabled",
    "validate_spectral", "data_assimilation", "prediction_mode",
}
_STR_KEYS = {"nu_b_profile"}


def _coerce_params(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _FLOAT_KEYS and v is not None:
            out[k] = float(v)
        elif k in _INT_KEYS and v is not None:
            out[k] = int(v)
        elif k in _BOOL_KEYS:
            out[k] = bool(v)
        elif k in _STR_KEYS:
            out[k] = str(v)
        else:
            out[k] = v
    return out


def _normalize_beta_aliases(p: dict[str, Any]) -> dict[str, Any]:
    """Map v5.2β keys to legacy field-engine aliases (α compatibility)."""
    pairs = [
        ("Gamma_h", "GAMMA_H"),
        ("Gamma_b", "GAMMA_B"),
        ("Gamma_a", "GAMMA_A"),
        ("rho0", "rho_a0"),
        ("Km", "K_m"),
        ("Omega0", "Omega0_init"),
        ("z_max", "z_roof"),
        ("island_depth", "d_iso"),
        ("eps_bump", "d_eps_iso"),
        ("Q_b", "Q_B"),
        ("CFL_max", "MICRO_DT_MAX"),
        ("CFL_max", "CFL_LIMIT"),
        ("amr_enabled", "gpu_amr_enabled"),
    ]
    for src, dst in pairs:
        if src in p and dst not in p:
            p[dst] = p[src]
        elif dst in p and src not in p:
            p[src] = p[dst]

    if "n_real0" in p and "n_real_amp" not in p:
        p["n_real_amp"] = float(p["n_real0"]) - 1.0
    elif "n_real_amp" in p and "n_real0" not in p:
        p["n_real0"] = 1.0 + float(p["n_real_amp"])

    return p


def load_params(*, reload: bool = False) -> dict[str, Any]:
    """Hot-load authoritative params.yml."""
    if not PARAMS_PATH.exists():
        raise FileNotFoundError(f"Missing parameter depot: {PARAMS_PATH}")
    with PARAMS_PATH.open(encoding="utf-8") as f:
        return _normalize_beta_aliases(_coerce_params(yaml.safe_load(f)))


def save_params(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into params.yml and export JSON for edge CDN."""
    current = load_params()
    current.update(updates)
    normalized = _normalize_beta_aliases(_coerce_params(current))
    PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PARAMS_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(normalized, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    export_params_json(normalized)
    return normalized


def export_params_json(params: dict[str, Any] | None = None) -> Path:
    """Bake params for edge worker / static CDN."""
    p = params or load_params()
    payload = {
        "version": "5.2β",
        "status": "all_constants_defined",
        "blocking_gaps": 0,
        "source": "params.yml",
        "params": p,
        "meta": {
            "L_f": p.get("L_f"),
            "coordinate_basis": "cylindrical (r, theta, z) statute miles",
            "origin": "Rupes Nigra peak",
            "time_zero": "polar midnight",
            "validation_anchor": "1982 Soviet Polar Expedition #122-85",
            "C_total": p["C_total"],
            "Omega_max": p["Omega_max"],
            "Z_g": p.get("Z_g"),
            "d_iso": p.get("d_iso", p.get("island_depth")),
            "toroidal_domain": {
                "r_max_mi": p["R_disk"],
                "z_max_mi": p.get("z_max", p.get("z_roof")),
                "z_T_mi": -abs(p.get("z_T", 3200)),
                "vertical_span_mi": abs(p.get("z_max", 700)) + abs(p.get("z_T", 3200)),
            },
        },
    }
    PUBLIC_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PARAMS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return PUBLIC_PARAMS_PATH


def load_node_table() -> list[dict[str, Any]]:
    """Parse node_table.csv into records."""
    import csv
    import math

    rows: list[dict[str, Any]] = []
    with NODE_TABLE_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            x, y, z = float(row["x_mi"]), float(row["y_mi"]), float(row["z_mi"])
            rows.append(
                {
                    "type": row["type"],
                    "x_mi": x,
                    "y_mi": y,
                    "z_mi": z,
                    "diameter_mi": float(row["diameter_mi"]),
                    "phase_deg": float(row["phase_deg"]),
                    "r_mi": math.hypot(x, y),
                    "theta_rad": math.atan2(y, x),
                    "altitude_mi": z,
                }
            )
    return rows


def load_luminary_spectra() -> list[dict[str, Any]]:
    """Sun/Moon emission lines from spectra/luminary_lines.csv."""
    import csv

    path = ROOT / "spectra" / "luminary_lines.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))