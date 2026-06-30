/** Planar field sampler — hydro inflow on (r, θ), no spherical math. */

export type SimParams = {
  Q_h: number;
  Gamma_h: number;
  sigma_h: number;
  r_sink: number;
  R_earth: number;
};

export const DEFAULT_SIM: SimParams = {
  Q_h: 0.87,
  Gamma_h: 24.6,
  sigma_h: 2.1,
  r_sink: 0.01,
  R_earth: 3959,
};

export function VrH(rMi: number, theta: number, P: SimParams): number {
  if (rMi <= P.r_sink) return -(P.Q_h * rMi) / (2 * Math.PI * P.r_sink ** 2);
  return (-(P.Q_h) / (2 * Math.PI * rMi)) * (1 + 0.4 * Math.cos(4 * theta));
}

export function flowMagnitude(rho: number, theta: number, P: SimParams): number {
  const rMi = Math.max(rho * P.R_earth, P.r_sink + 1e-6);
  const vr = VrH(rMi, theta, P);
  return Math.abs(vr);
}