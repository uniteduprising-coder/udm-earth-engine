"""
UDM Cosmology Engine v5.2α — analytic field functions.
NumPy-free scalar implementations for edge/API parity.
"""

from __future__ import annotations

import math
from typing import Any


def rupes_radius_profile(z: float, P: dict[str, Any]) -> float:
    """Tapered cone r(z) for 0 ≤ z ≤ h_peak."""
    if z <= 0:
        return P["r_base"]
    if z >= P["h_peak"]:
        return P["r_summit"]
    return P["r_base"] - (P["r_base"] - P["r_summit"]) * (z / P["h_peak"])


def island_theta(n: int) -> float:
    return math.pi / 4 + n * (math.pi / 2)


def B0_field(P: dict[str, Any]) -> float:
    """B₀ = μ₀·M₀/(2π·r_base²) — use ledger value when present."""
    if "B0" in P:
        return float(P["B0"])
    return P["mu0"] * P["M0"] / (2 * math.pi * P["r_base"] ** 2)


def B_stat(r: float, theta: float, P: dict[str, Any]) -> float:
    """Vertical dipole with 4-fold modulation (§4.2)."""
    B0 = B0_field(P)
    return B0 * (P["r_base"] / r) ** 2 * (1 + P["B_mod_amp"] * math.cos(4 * theta))


def sigma_iso_eff(E: float, P: dict[str, Any]) -> float:
    """Conductivity saturation σ_iso·tanh(E/E_crit) (§2.2)."""
    return P["sigma_iso"] * math.tanh(E / P["E_crit"])


def n_firmament_real(z: float, P: dict[str, Any]) -> float:
    """n'(z) = 1 + amp·exp(−z/scale) (§5.2, §6.3)."""
    return 1.0 + P["n_real_amp"] * math.exp(-z / P["n_real_scale"])


def n_firmament_imag(z: float, P: dict[str, Any]) -> float:
    """n''(z) = n''₀·exp(−z/scale)."""
    return P["n_imag0"] * math.exp(-z / P["n_imag_scale"])


def schumann_q_factor(P: dict[str, Any]) -> float:
    """Q = f_res / Δf."""
    return P.get("schumann_Q", P.get("f_res", 25) / P.get("schumann_df_Hz", 2.5))


def eps_field(r: float, theta: float, P: dict[str, Any]) -> float:
    """Disk permittivity + four Gaussian islands (§1)."""
    base = P["eps0"] * (1 + 2.5 * P["r_base"] / r)
    for n in range(4):
        th_iso = island_theta(n)
        dtheta = theta - th_iso
        dr = r - P["r_iso"]
        base += (
            P["d_eps_iso"]
            * P["eps0"]
            * math.exp(-(dr**2) / (2 * P["a_iso"] ** 2) - (dtheta**2) / (2 * P["sigma_theta"] ** 2))
        )
    return base


def rho_a_field(r: float, theta: float, t: float, P: dict[str, Any]) -> float:
    """Aether density travelling wave (§2)."""
    return P["rho_a0"] * (P["r_base"] / r) ** 2 * math.cos(P["m_a"] * theta - P["omega_a"] * t)


def V_theta_h(r: float, P: dict[str, Any]) -> float:
    if r <= P["r_sink"]:
        return (P["GAMMA_H"] * r) / (2 * math.pi * P["r_sink"] ** 2)
    return (P["GAMMA_H"] / (2 * math.pi * r)) * (1 - math.exp(-(r**2) / (2 * P["sigma_h"] ** 2)))


def V_r_h(r: float, theta: float, P: dict[str, Any]) -> float:
    if r <= P["r_sink"]:
        return -(P["Q_h"] * r) / (2 * math.pi * P["r_sink"] ** 2)
    return -(P["Q_h"] / (2 * math.pi * r)) * (1 + 0.4 * math.cos(4 * theta))


def V_theta_a(r: float, P: dict[str, Any]) -> float:
    if r <= P["r_sink_a"]:
        return 0.0
    return (P["GAMMA_A"] / (2 * math.pi * r)) * (1 - math.exp(-(r**2) / (2 * P["sigma_a"] ** 2)))


def V_r_a(r: float, P: dict[str, Any]) -> float:
    if r <= P["r_sink_a"]:
        return -(P["Q_a"] * r) / (2 * math.pi * P["r_sink_a"] ** 2)
    return -(P["Q_a"] / (2 * math.pi * r))


def V_z_h(z: float, P: dict[str, Any]) -> float:
    if z < 2.0:
        return -P["W_h"] * (z / P["h_peak"])
    return 0.0


def motional_emf(r: float, theta: float, omega0: float, P: dict[str, Any]) -> float:
    """Radial motional EMF: v_rot × B_stat (§3)."""
    v_rot_theta = omega0 * (P["r_base"] / r) ** 2 * r
    return v_rot_theta * B_stat(r, theta, P)


def omega_firm(r: float, z: float, omega0: float, P: dict[str, Any]) -> float:
    """Rotor angular velocity with Rayleigh shear (§4)."""
    base = omega0 * (P["r_base"] / r) ** 2
    if z > 500.0:
        base *= math.exp(-P["eta_shear"] * (z - 500.0))
    return base


def glow_intensity(r: float, theta: float, t: float, P: dict[str, Any]) -> float:
    """Simplified luminosity at (r,θ,t) — analytic proxy (§2)."""
    if r < P["r_sink_a"]:
        return 0.0
    va_t = V_theta_a(r, P)
    va_r = V_r_a(r, P)
    rho = rho_a_field(r, theta, t, P)
    curl_proxy = (va_t / r) ** 2 + (va_r / max(r, 0.1)) ** 2
    grad_rho = -2 * P["rho_a0"] * (P["r_base"] / r) ** 3 * math.cos(P["m_a"] * theta - P["omega_a"] * t)
    v_dot_grad = va_r * grad_rho
    return (
        P["LUM_BETA"]
        * (curl_proxy + P["LUM_GAMMA"] * v_dot_grad**2)
        * math.exp(-r / P["lambda_abs"])
    )


def T_drag(omega0: float, P: dict[str, Any]) -> float:
    return -P["kappa"] * omega0**1.8


def T_em_sample(r: float, theta: float, omega0: float, P: dict[str, Any]) -> float:
    """Point sample of EM torque integrand r·J_r·B_z."""
    emf = motional_emf(r, theta, omega0, P)
    jr = P["sigma_eff"] * emf
    return r * jr * B_stat(r, theta, P)


def glow_azimuthal_ratio(r: float, t: float, P: dict[str, Any]) -> float:
    """Peak/antipeak ratio of |I(r,θ,t)| ∝ |cos(4θ)| — check #15."""
    peak = abs(glow_intensity(r, 0.0, t, P))
    antipeak = abs(glow_intensity(r, math.pi / 4, t, P))
    if antipeak < 1e-12:
        return 0.0
    return peak / antipeak


def compute_I_rot(P: dict[str, Any]) -> float:
    """Rotor inertia I_rot ≈ ∫ρ_a·r²·dV over firmament shell (§4.3)."""
    if "I_rot" in P:
        return float(P["I_rot"])
    z_max = P["z_roof"]
    r_min, r_max = P["r_base"], P["R_disk"]
    rho0 = P["rho_a0"]
    rb = P["r_base"]
    # Shell integral proxy: 2π·z_max·∫ r³·(rb/r)² dr
    integral = 2 * math.pi * z_max * (rb**2) * math.log(r_max / r_min)
    return rho0 * integral * (1609.344**2)  # mi² → m² for kg·m² scale