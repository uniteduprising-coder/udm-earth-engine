(function () {
  const F = window.UDM_FIELDS;
  const $ = (id) => document.getElementById(id);
  const GRID = 256;
  const ARROW_STEP = 18;

  let params = {};
  let state = {
    t_sim: 0,
    macro_step: 0,
    omega0: 2.45,
    aborted: false,
    abort_reason: "",
    playing: true,
  };

  let canvas, ctx;
  let fieldMode = "flow";
  let showVectors = true;
  let showRings = true;
  let diskMeta = { outer_radius_px: 1012 };
  let features = [];
  let lastFrame = 0;
  let stepAccumulator = 0;

  const PALETTES = {
    flow: (v, max) => heat(v / max, [10, 20, 40], [40, 180, 255], [255, 240, 120]),
    glow: (v, max) => heat(v / max, [8, 8, 20], [180, 60, 255], [255, 220, 140]),
    bstat: (v, max) => heat(v / max, [5, 10, 25], [80, 120, 220], [220, 240, 255]),
    rhoa: (v, max) => heat(v / max, [12, 8, 28], [60, 180, 140], [200, 255, 200]),
    vr: (v, max) => heat(v / max, [15, 10, 30], [200, 80, 60], [255, 200, 80]),
  };

  function heat(t, c0, c1, c2) {
    const x = Math.max(0, Math.min(1, t));
    const a = x < 0.5 ? c0 : c1;
    const b = x < 0.5 ? c1 : c2;
    const u = x < 0.5 ? x * 2 : (x - 0.5) * 2;
    return [
      Math.round(a[0] + (b[0] - a[0]) * u),
      Math.round(a[1] + (b[1] - a[1]) * u),
      Math.round(a[2] + (b[2] - a[2]) * u),
    ];
  }

  function normalizeParams(raw) {
    const p = { ...raw };
    if (p.rho0 != null && p.rho_a0 == null) p.rho_a0 = p.rho0;
    if (p.Omega0 != null && p.Omega0_init == null) p.Omega0_init = p.Omega0;
    if (p.Gamma_h != null && p.GAMMA_H == null) p.GAMMA_H = p.Gamma_h;
    if (p.Gamma_a != null && p.GAMMA_A == null) p.GAMMA_A = p.Gamma_a;
    if (p.Q_b != null && p.Q_B == null) p.Q_B = p.Q_b;
    return p;
  }

  function macroStepLocal() {
    if (state.aborted) return;
    const omegaPrev = state.omega0;
    state.omega0 = F.newtonRaphsonOmega(omegaPrev, params);
    const glow70 = F.glowIntensity(70, Math.PI / 4, state.t_sim, params);
    if (state.omega0 > params.Omega_max) {
      state.aborted = true;
      state.abort_reason = `Ω₀ exceeds ${params.Omega_max} rad/s`;
    }
    if (glow70 > (params.I_max || 1e6)) {
      state.aborted = true;
      state.abort_reason = "Glow intensity exceeds I_max";
    }
    state.t_sim += params.DT_MACRO || 15;
    state.macro_step += 1;
    updateTelemetry();
  }

  async function macroStepRemote() {
    try {
      const r = await fetch("/api/cosmology/step?steps=1", { method: "POST" });
      if (!r.ok) throw new Error(String(r.status));
      const data = await r.json();
      const rec = data.records?.[data.records.length - 1] || {};
      const st = data.state || {};
      state.omega0 = st.Omega0 ?? rec.Omega0 ?? state.omega0;
      state.t_sim = st.t_sim_s ?? rec.t_sim_s ?? state.t_sim;
      state.macro_step = st.macro_step ?? rec.macro_step ?? state.macro_step;
      state.aborted = !!st.aborted;
      state.abort_reason = st.abort_reason || "";
      updateTelemetry();
      return true;
    } catch {
      macroStepLocal();
      return false;
    }
  }

  function updateTelemetry() {
    const pgw = F.powerGw(state.omega0, params);
    const { tEm, tDrag } = F.torqueSum(state.omega0, params);
    $("ps-telemetry").textContent = [
      `t_sim: ${state.t_sim.toFixed(1)} s`,
      `macro_step: ${state.macro_step}`,
      `Ω₀: ${state.omega0.toFixed(4)} rad/s`,
      `P_GW: ${pgw.toFixed(3)}`,
      `T_em: ${tEm.toFixed(2)}  T_drag: ${tDrag.toFixed(2)}`,
      `Q_h: ${params.Q_h} mi³/s (planar inflow)`,
      state.aborted ? `ABORT: ${state.abort_reason}` : "status: running",
    ].join("\n");
    $("ps-status").textContent = state.aborted
      ? `Simulation aborted — ${state.abort_reason}`
      : `Planar engine · ${fieldMode} field · step Δt=${params.DT_MACRO || 15}s`;
  }

  function renderField() {
    const w = GRID;
    const h = GRID;
    const img = ctx.createImageData(w, h);
    const data = img.data;
    const cx = w / 2;
    const cy = h / 2;
    const R = w / 2 - 2;
    let vmax = 1e-9;

    const samples = new Float32Array(w * h);
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const dx = i - cx;
        const dy = j - cy;
        const dist = Math.hypot(dx, dy);
        const idx = j * w + i;
        if (dist > R) {
          samples[idx] = -1;
          continue;
        }
        const rho = dist / R;
        const theta = Math.atan2(dx, dy);
        const v = F.samplePlanar(rho, theta, state.t_sim, state.omega0, params, fieldMode);
        samples[idx] = v;
        if (v > vmax) vmax = v;
      }
    }

    const palette = PALETTES[fieldMode] || PALETTES.flow;
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const idx = j * w + i;
        const p = (j * w + i) * 4;
        if (samples[idx] < 0) {
          data[p] = 6;
          data[p + 1] = 10;
          data[p + 2] = 16;
          data[p + 3] = 255;
          continue;
        }
        const [r, g, b] = palette(samples[idx], vmax);
        data[p] = r;
        data[p + 1] = g;
        data[p + 2] = b;
        data[p + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);

    if (showVectors) drawVectors(cx, cy, R);
    if (showRings) drawRings(cx, cy, R);
    drawNorthMark(cx, cy);
  }

  function drawVectors(cx, cy, R) {
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.55)";
    ctx.lineWidth = 1;
    for (let j = ARROW_STEP; j < GRID; j += ARROW_STEP) {
      for (let i = ARROW_STEP; i < GRID; i += ARROW_STEP) {
        const dx = i - cx;
        const dy = j - cy;
        const dist = Math.hypot(dx, dy);
        if (dist > R * 0.95 || dist < R * 0.02) continue;
        const rho = dist / R;
        const theta = Math.atan2(dx, dy);
        const v = F.flowVector(rho, theta, params);
        const scale = 6 / Math.max(0.02, v.mag);
        const x1 = i;
        const y1 = j;
        const x2 = i + v.x * scale;
        const y2 = j + v.y * scale;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  function drawRings(cx, cy, R) {
    ctx.save();
    features
      .filter((f) => /rupes|island_outer|equator|arctic|rim/.test(f.name))
      .forEach((f) => {
        const r = (f.px_from_center / (diskMeta.outer_radius_px || 1012)) * R;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = f.name.includes("rupes")
          ? "rgba(200, 100, 255, 0.85)"
          : f.name.includes("island")
            ? "rgba(100, 220, 255, 0.8)"
            : "rgba(120, 160, 220, 0.45)";
        ctx.lineWidth = f.name.includes("rupes") ? 2 : 1;
        ctx.setLineDash(f.name.includes("rim") ? [5, 4] : []);
        ctx.stroke();
      });
    ctx.setLineDash([]);
    ctx.restore();
  }

  function drawNorthMark(cx, cy) {
    ctx.save();
    ctx.fillStyle = "rgba(0, 255, 220, 0.95)";
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.font = "11px Segoe UI";
    ctx.fillText("N aperture", cx + 7, cy - 5);
    ctx.restore();
  }

  function loop(ts) {
    requestAnimationFrame(loop);
    if (!state.playing || state.aborted) {
      if (ts - lastFrame > 250) {
        renderField();
        lastFrame = ts;
      }
      return;
    }
    stepAccumulator += ts - (lastFrame || ts);
    lastFrame = ts;
    const stepMs = 120;
    while (stepAccumulator >= stepMs) {
      macroStepLocal();
      stepAccumulator -= stepMs;
    }
    renderField();
  }

  async function loadParams() {
    const r = await fetch("/api/params");
    const data = await r.json();
    params = normalizeParams(data.params || data);
    state.omega0 = params.Omega0_init ?? params.Omega0 ?? 2.45;
    try {
      const terms = await fetch("/api/procedural/terminations").then((x) => x.json());
      features = terms.features || [];
      diskMeta = terms.disk || diskMeta;
    } catch {
      features = [];
    }
    updateTelemetry();
  }

  function bindUi() {
    $("ps-field")?.addEventListener("change", (e) => {
      fieldMode = e.target.value;
      renderField();
    });
    $("ps-vectors")?.addEventListener("change", (e) => {
      showVectors = e.target.checked;
      renderField();
    });
    $("ps-rings")?.addEventListener("change", (e) => {
      showRings = e.target.checked;
      renderField();
    });
    $("ps-play")?.addEventListener("click", () => {
      state.playing = !state.playing;
      $("ps-play").textContent = state.playing ? "Pause" : "Play";
    });
    $("ps-step")?.addEventListener("click", () => macroStepRemote().then(() => renderField()));
    $("ps-reset")?.addEventListener("click", async () => {
      try {
        await fetch("/api/cosmology/reset", { method: "POST" });
      } catch {
        /* local reset */
      }
      state.t_sim = 0;
      state.macro_step = 0;
      state.omega0 = params.Omega0_init ?? 2.45;
      state.aborted = false;
      state.abort_reason = "";
      state.playing = true;
      $("ps-play").textContent = "Pause";
      updateTelemetry();
      renderField();
    });
  }

  window.addEventListener("load", async () => {
    canvas = $("ps-canvas");
    ctx = canvas.getContext("2d", { willReadFrequently: true });
    canvas.width = GRID;
    canvas.height = GRID;
    bindUi();
    await loadParams();
    renderField();
    requestAnimationFrame(loop);
  });
})();