"""
UDM Cosmology Engine — analytic warm-start + macro-step state machine.
Full GPU solver deferred; API exposes self-consistent telemetry per spec §7–§8.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from earth.cosmology import fields
from earth.cosmology.params import load_node_table, load_params


@dataclass
class CosmologyEngine:
    """Singleton-style engine with hot-reloadable parameters."""

    params: dict[str, Any] = field(default_factory=load_params)
    omega0: float = field(init=False)
    t_sim: float = 0.0
    macro_step: int = 0
    warm_start: bool = True
    aborted: bool = False
    abort_reason: str = ""
    telemetry: list[dict[str, Any]] = field(default_factory=list)
    _started_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.omega0 = self.params["Omega0_init"]
        self.restart_micro_loop()

    def restart_micro_loop(self) -> None:
        """Called after params.yml rewrite (§0)."""
        self._started_at = time.time()

    def reload_params(self, params: dict[str, Any] | None = None) -> None:
        self.params = params or load_params()
        self.restart_micro_loop()

    def _torque_sum(self, omega: float) -> tuple[float, float]:
        P = self.params
        t_em = sum(
            fields.T_em_sample(P["r_iso"], fields.island_theta(n), omega, P) for n in range(4)
        )
        return t_em, fields.T_drag(omega, P)

    def newton_raphson_omega(self, omega_prev: float | None = None) -> float:
        """Solve I_rot·dΩ/dt = T_em + T_drag; NR steady-state refine (§4.6)."""
        P = self.params
        omega = self.omega0
        i_rot = P.get("I_rot", 2.3e24)
        if omega_prev is not None and i_rot > 0:
            t_em, t_drag = self._torque_sum(omega_prev)
            omega = omega_prev + (t_em + t_drag) / i_rot * P["DT_MACRO"]
        for _ in range(5):
            t_em, t_drag = self._torque_sum(omega)
            f = t_em + t_drag
            d_omega = 1e-4
            t_em_p, t_drag_p = self._torque_sum(omega + d_omega)
            df = (t_em_p + t_drag_p - f) / d_omega
            if abs(df) < 1e-12:
                break
            omega -= f / df
            if abs(f) < 1e-4:
                break
        return omega

    def compute_power_gw(self) -> float:
        """Total extracted power P = Σ P_n (§3), GW scale."""
        P = self.params
        r = P["r_iso"]
        power_w = 0.0
        for n in range(4):
            th = fields.island_theta(n)
            emf = fields.motional_emf(r, th, self.omega0, P)
            jr = P["sigma_eff"] * emf
            area = 2 * math.pi * r * P["a_iso"]
            power_w += abs(jr * emf * area)
        return power_w / 1e9

    def macro_step_tick(self) -> dict[str, Any]:
        """Advance one macro-step (Δt_macro = 15 s)."""
        P = self.params
        if self.aborted:
            return self.state()

        omega_prev = self.omega0
        self.omega0 = self.newton_raphson_omega(omega_prev)
        t_em = sum(fields.T_em_sample(P["r_iso"], fields.island_theta(n), self.omega0, P) for n in range(4))
        t_drag = fields.T_drag(self.omega0, P)
        power = self.compute_power_gw()
        glow_70 = fields.glow_intensity(70.0, math.pi / 4, self.t_sim, P)
        vr_h_1 = fields.V_r_h(1.0, 0.0, P)
        vr_a_1 = fields.V_r_a(1.0, P)

        if self.omega0 > P["Omega_max"]:
            self.aborted = True
            self.abort_reason = f"Dielectric breakdown — Ω₀ exceeds {P['Omega_max']} rad/s (E_break limit)"
        if glow_70 > P["I_max"]:
            self.aborted = True
            self.abort_reason = "Unphysical flash — glow intensity > 1e6 cd"

        record = {
            "macro_step": self.macro_step,
            "t_sim_s": self.t_sim,
            "Omega0": round(self.omega0, 6),
            "T_em": round(t_em, 4),
            "T_drag": round(t_drag, 4),
            "P_GW": round(power, 4),
            "I_70_pi4_cd": round(glow_70, 2),
            "V_r_h_1_mi_s": round(vr_h_1, 6),
            "V_r_a_1_mi_s": round(vr_a_1, 6),
            "warm_start": self.warm_start and self.macro_step < 100,
        }
        self.telemetry.append(record)
        if len(self.telemetry) > 200:
            self.telemetry = self.telemetry[-200:]

        self.macro_step += 1
        self.t_sim += P["DT_MACRO"]
        if self.macro_step >= 100:
            self.warm_start = False

        return record

    def state(self) -> dict[str, Any]:
        """Current engine state for API / WebSocket."""
        P = self.params
        r, th = 70.0, math.pi / 4
        return {
            "version": "5.2α",
            "engine": "udm_cosmology",
            "status": "all_constants_defined",
            "t_sim_s": self.t_sim,
            "macro_step": self.macro_step,
            "Omega0": round(self.omega0, 6),
            "Omega0_init": P["Omega0_init"],
            "Omega_max": P["Omega_max"],
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "warm_start": self.warm_start,
            "P_GW": round(self.compute_power_gw(), 4),
            "P_target_GW": P["P_target"],
            "C_total_F": P["C_total"],
            "Z_g_ohm": P.get("Z_g", 2.8),
            "I_rot_kgm2": P.get("I_rot", 2.3e24),
            "Q_visc_GW": round(P.get("Q_visc", 4e8) / 1e9, 2),
            "omega_res_Hz": P.get("f_res", round(P["omega_res"] / (2 * math.pi), 2)),
            "schumann_Q": round(fields.schumann_q_factor(P), 1),
            "T_a_period_min": P["T_a_period_min"],
            "firmament_n_z0": {
                "n_real": round(fields.n_firmament_real(0, P), 6),
                "n_imag": round(fields.n_firmament_imag(0, P), 8),
            },
            "fields_at_anchor": {
                "r_mi": r,
                "theta_rad": round(th, 6),
                "I_cd": round(fields.glow_intensity(r, th, self.t_sim, P), 2),
                "B_stat_T": round(fields.B_stat(r, th, P), 8),
                "rho_a": round(fields.rho_a_field(r, th, self.t_sim, P), 12),
                "V_r_h": round(fields.V_r_h(r, th, P), 8),
                "V_r_a": round(fields.V_r_a(r, P), 8),
            },
            "nodes": load_node_table(),
            "uptime_s": round(time.time() - self._started_at, 1),
        }

    def field_sample(
        self,
        r_mi: float,
        theta_rad: float,
        *,
        z_mi: float = 0.0,
        t_s: float | None = None,
    ) -> dict[str, Any]:
        """Sample all primary fields at a point."""
        t = self.t_sim if t_s is None else t_s
        P = self.params
        return {
            "r_mi": r_mi,
            "theta_rad": theta_rad,
            "z_mi": z_mi,
            "t_s": t,
            "B_stat_T": fields.B_stat(r_mi, theta_rad, P),
            "eps_F_m": fields.eps_field(r_mi, theta_rad, P),
            "rho_a": fields.rho_a_field(r_mi, theta_rad, t, P),
            "V_h": {
                "r": fields.V_r_h(r_mi, theta_rad, P),
                "theta": fields.V_theta_h(r_mi, P),
                "z": fields.V_z_h(z_mi, P),
            },
            "V_a": {
                "r": fields.V_r_a(r_mi, P),
                "theta": fields.V_theta_a(r_mi, P),
            },
            "I_cd": fields.glow_intensity(r_mi, theta_rad, t, P),
            "E_mot": fields.motional_emf(r_mi, theta_rad, self.omega0, P),
            "Omega_firm": fields.omega_firm(r_mi, z_mi, self.omega0, P),
            "n_real": fields.n_firmament_real(z_mi, P),
            "n_imag": fields.n_firmament_imag(z_mi, P),
            "Z_g": P.get("Z_g", 2.8),
        }


_ENGINE: CosmologyEngine | None = None


def get_engine() -> CosmologyEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = CosmologyEngine()
    return _ENGINE


def reset_engine(params: dict[str, Any] | None = None) -> CosmologyEngine:
    global _ENGINE
    _ENGINE = CosmologyEngine(params=params or load_params())
    return _ENGINE