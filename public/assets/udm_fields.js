/** UDM v5.2β planar field functions — mirrors earth.cosmology.fields (scalar JS). */
(function (root) {
  const TAU = Math.PI * 2;

  function islandTheta(n) {
    return Math.PI / 4 + n * (Math.PI / 2);
  }

  function B0(P) {
    if (P.B0 != null) return P.B0;
    return (P.mu0 * P.M0) / (2 * Math.PI * P.r_base ** 2);
  }

  function Bstat(r, theta, P) {
    const b0 = B0(P);
    return b0 * (P.r_base / r) ** 2 * (1 + P.B_mod_amp * Math.cos(4 * theta));
  }

  function rhoA(r, theta, t, P) {
    const rho0 = P.rho_a0 ?? P.rho0 ?? 1.2e-6;
    return rho0 * (P.r_base / r) ** 2 * Math.cos(P.m_a * theta - P.omega_a * t);
  }

  function VthetaH(r, P) {
    if (r <= P.r_sink) return (P.Gamma_h * r) / (2 * Math.PI * P.r_sink ** 2);
    return (P.Gamma_h / (2 * Math.PI * r)) * (1 - Math.exp(-(r ** 2) / (2 * P.sigma_h ** 2)));
  }

  function VrH(r, theta, P) {
    if (r <= P.r_sink) return -(P.Q_h * r) / (2 * Math.PI * P.r_sink ** 2);
    return -(P.Q_h / (2 * Math.PI * r)) * (1 + 0.4 * Math.cos(4 * theta));
  }

  function VthetaA(r, P) {
    if (r <= P.r_sink_a) return 0;
    return (P.Gamma_a / (2 * Math.PI * r)) * (1 - Math.exp(-(r ** 2) / (2 * P.sigma_a ** 2)));
  }

  function VrA(r, P) {
    if (r <= P.r_sink_a) return -(P.Q_a * r) / (2 * Math.PI * P.r_sink_a ** 2);
    return -(P.Q_a / (2 * Math.PI * r));
  }

  function motionalEmf(r, theta, omega0, P) {
    const vRotTheta = omega0 * (P.r_base / r) ** 2 * r;
    return vRotTheta * Bstat(r, theta, P);
  }

  function glowIntensity(r, theta, t, P) {
    if (r < P.r_sink_a) return 0;
    const vaT = VthetaA(r, P);
    const vaR = VrA(r, P);
    const gradRho =
      -2 * (P.rho_a0 ?? P.rho0) * (P.r_base / r) ** 3 * Math.cos(P.m_a * theta - P.omega_a * t);
    const curlProxy = (vaT / r) ** 2 + (vaR / Math.max(r, 0.1)) ** 2;
    const vDotGrad = vaR * gradRho;
    return (
      P.LUM_BETA *
      (curlProxy + P.LUM_GAMMA * vDotGrad ** 2) *
      Math.exp(-r / P.lambda_abs)
    );
  }

  function Tdrag(omega0, P) {
    return -P.kappa * omega0 ** 1.8;
  }

  function TemSample(r, theta, omega0, P) {
    const emf = motionalEmf(r, theta, omega0, P);
    const jr = P.sigma_eff * emf;
    return r * jr * Bstat(r, theta, P);
  }

  function torqueSum(omega0, P) {
    let tem = 0;
    for (let n = 0; n < 4; n++) {
      tem += TemSample(P.r_iso, islandTheta(n), omega0, P);
    }
    return { tEm: tem, tDrag: Tdrag(omega0, P) };
  }

  function newtonRaphsonOmega(omegaPrev, P) {
    let omega = omegaPrev;
    const iRot = P.I_rot ?? 2.3e24;
    if (omegaPrev != null && iRot > 0) {
      const { tEm, tDrag } = torqueSum(omegaPrev, P);
      omega = omegaPrev + ((tEm + tDrag) / iRot) * P.DT_MACRO;
    }
    for (let i = 0; i < 5; i++) {
      const { tEm, tDrag } = torqueSum(omega, P);
      const f = tEm + tDrag;
      const dOmega = 1e-4;
      const plus = torqueSum(omega + dOmega, P);
      const df = (plus.tEm + plus.tDrag - f) / dOmega;
      if (Math.abs(df) < 1e-12) break;
      omega -= f / df;
      if (Math.abs(f) < 1e-4) break;
    }
    return omega;
  }

  function powerGw(omega0, P) {
    let powerW = 0;
    for (let n = 0; n < 4; n++) {
      const th = islandTheta(n);
      const r = P.r_iso;
      const emf = motionalEmf(r, th, omega0, P);
      const jr = P.sigma_eff * emf;
      const area = 2 * Math.PI * r * P.a_iso;
      powerW += Math.abs(jr * emf * area);
    }
    return powerW / 1e9;
  }

  function samplePlanar(rho, theta, t, omega0, P, field) {
    const r = Math.max(rho * P.R_earth, P.r_sink + 1e-6);
    switch (field) {
      case "flow": {
        const vr = VrH(r, theta, P);
        const vt = VthetaH(r, P);
        return Math.hypot(vr, vt);
      }
      case "vr":
        return Math.abs(VrH(r, theta, P));
      case "glow":
        return glowIntensity(r, theta, t, P);
      case "bstat":
        return Math.abs(Bstat(r, theta, P));
      case "rhoa":
        return Math.abs(rhoA(r, theta, t, P));
      case "emf":
        return Math.abs(motionalEmf(r, theta, omega0, P));
      default:
        return 0;
    }
  }

  function flowVector(rho, theta, P) {
    const r = Math.max(rho * P.R_earth, P.r_sink + 1e-6);
    const vr = VrH(r, theta, P);
    const vt = VthetaH(r, P);
    const ex = Math.sin(theta);
    const ey = Math.cos(theta);
    const etx = Math.cos(theta);
    const ety = -Math.sin(theta);
    return { x: vr * ex + vt * etx, y: vr * ey + vt * ety, mag: Math.hypot(vr, vt) };
  }

  root.UDM_FIELDS = {
    islandTheta,
    Bstat,
    rhoA,
    VrH,
    VthetaH,
    glowIntensity,
    newtonRaphsonOmega,
    powerGw,
    samplePlanar,
    flowVector,
    torqueSum,
  };
})(typeof window !== "undefined" ? window : globalThis);