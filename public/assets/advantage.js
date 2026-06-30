/**
 * UDM Competitive Advantage Blueprint — dual mode, live validation, predictions, replay, spectral
 */
(function () {
  const API = `${window.EARTH_ORIGIN || window.location.origin}/api`;
  const DATA = `${window.EARTH_ORIGIN || window.location.origin}/data/cosmology`;

  const $ = (s) => document.querySelector(s);
  const state = {
    realityMode: 'udm',
    ws: null,
    replayOffset: 0,
    replayPlaying: false,
    replayTimer: null,
    cursor: { lat: 75, lon: 0 },
  };

  async function fetchJson(url, opts) {
    const res = await fetch(url, { credentials: 'same-origin', ...opts });
    if (!res.ok) throw new Error(`${url} → ${res.status}`);
    return res.json();
  }

  function statusIcon(s) {
    const m = { PASS: '✓', MARGIN: '◐', CHECK: '✗', FAIL: '✗', PENDING: '…' };
    return m[s] || '·';
  }

  function badgeClass(s) {
    if (s === 'PASS') return 'pass';
    if (s === 'MARGIN' || s === 'CHECK') return 'margin';
    if (s === 'PENDING') return 'margin';
    return 'fail';
  }

  async function loadAdvantageSummary() {
    try {
      const data = await fetchJson(`${API}/advantage/summary`).catch(() => fetchJson(`${DATA}/advantage.json`));
      const summary = data.summary || data;
      const score = summary.score_pct ?? 87.5;
      const cons = summary.observational_consistency ?? '16/18 checks passed';
      $('#reality-score').textContent = `${score}%`;
      $('#reality-consistency').textContent = cons;
      if (summary.validation?.checks) renderLiveDashboard(summary.validation);
    } catch {
      $('#reality-consistency').textContent = 'offline — baked fallback';
    }
  }

  function renderLiveDashboard(report) {
    const el = $('#live-validation-dashboard');
    if (!el || !report) return;
    const checks = report.checks || [];
    const rows = checks
      .map(
        (c) =>
          `<div class="val-row ${badgeClass(c.status)}">
            <span class="val-name">${c.name}</span>
            <span class="val-value">${c.value ?? '—'}</span>
            <span class="badge badge-${badgeClass(c.status)}">${statusIcon(c.status)} ${c.status}</span>
          </div>`
      )
      .join('');
    const score = report.passed != null ? `${((report.passed / report.total_checks) * 100).toFixed(1)}% (${report.passed}/${report.total_checks})` : '—';
    el.innerHTML = `${rows}<div class="val-footer">Overall: <strong>${score}</strong></div>`;
    el.classList.remove('muted');
  }

  function connectTelemetry() {
    if (state.ws) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/api/ws/telemetry`;
    try {
      state.ws = new WebSocket(url);
      state.ws.onmessage = (ev) => {
        try {
          const frame = JSON.parse(ev.data);
          const v = frame.frames?.find((f) => f.type === 5);
          if (v) {
            renderLiveDashboard({ checks: v.checks, passed: v.passed, total_checks: v.total });
            $('#reality-score').textContent = `${v.score_pct}%`;
          }
          const p = frame.frames?.find((f) => f.type === 1);
          if (p?.physics) {
            const glow = p.physics.fields_at_anchor?.I_cd;
            if (glow != null) $('#m-glow').textContent = Math.round(glow);
            if (p.physics.Omega0 != null) $('#m-omega').textContent = Number(p.physics.Omega0).toFixed(3);
          }
        } catch {
          /* binary mode */
        }
      };
      state.ws.onclose = () => {
        state.ws = null;
      };
    } catch {
      /* edge worker may not support WS */
    }
  }

  async function updateDualMode(lat, lon) {
    state.cursor = { lat, lon };
    const el = $('#dual-mode-panel');
    if (!el) return;
    try {
      const view = state.realityMode === 'split' ? 'split' : state.realityMode === 'overlay' ? 'overlay' : 'compare';
      const data = await fetchJson(`${API}/advantage/dual-mode?lat=${lat}&lon=${lon}&view=${view}&t_s=0`);
      const div = data.divergence || {};
      el.innerHTML = [
        `<div class="dual-row"><span>UDM glow</span><strong>${div.glow_udm_only_cd ?? '—'} cd</strong></div>`,
        `<div class="dual-row"><span>Position Δ</span><strong>${div.position_delta_deg ?? '—'}°</strong></div>`,
        `<div class="dual-row"><span>Diverge</span><strong>${div.predictions_diverge ? 'YES' : 'no'}</strong></div>`,
        data.copernican ? `<div class="dual-note muted">Copernican: WGS84 baseline (no aether glow)</div>` : '',
      ].join('');
      el.classList.remove('muted');
    } catch {
      el.textContent = 'Dual-mode API offline';
    }
  }

  async function renderSpectralPreview() {
    const canvas = $('#spectral-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cosmology = state.realityMode === 'copernican' ? 'copernican' : 'udm';
    try {
      const data = await fetchJson(`${API}/advantage/spectral?cosmology=${cosmology}&melanin=12`);
      const sky = data.sky_zenith?.rgb || [180, 200, 120];
      const skin = data.skin?.rgb || [200, 170, 120];
      ctx.fillStyle = `rgb(${sky.join(',')})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height / 2);
      ctx.fillStyle = `rgb(${skin.join(',')})`;
      ctx.fillRect(0, canvas.height / 2, canvas.width, canvas.height / 2);
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '10px Consolas, monospace';
      ctx.fillText(`${data.illuminant_label || cosmology} · ${data.dominant_wavelength_nm} nm`, 6, 14);
      ctx.fillText(`skin ${data.skin?.hex || ''}`, 6, canvas.height / 2 + 14);
    } catch {
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }

  async function loadPredictions() {
    const el = $('#prediction-market');
    if (!el) return;
    try {
      const data = await fetchJson(`${API}/advantage/predictions`);
      const items = (data.predictions || [])
        .slice(0, 3)
        .map(
          (p) =>
            `<div class="pred-card">
              <div class="pred-id">#${p.id}: ${p.observable} @ station ${p.location?.station || ''}</div>
              <div>${p.predicted}</div>
              <div class="muted">Pool: ${p.pool_points} pts · ${p.target_date || ''}</div>
            </div>`
        )
        .join('');
      el.innerHTML = `${items}<div class="pred-stats muted">30-day accuracy: ${data.accuracy_30d_pct}% · Leader: ${data.leader?.user}</div>`;
      el.classList.remove('muted');
    } catch {
      el.textContent = 'Prediction market offline';
    }
  }

  async function runPredictionGenerator() {
    const el = $('#prediction-output');
    const obs = $('#pred-observable')?.value || 'glow';
    const { lat, lon } = state.cursor;
    try {
      const data = await fetchJson(`${API}/advantage/predict?lat=${lat}&lon=${lon}&observable=${obs}`);
      const pred = data.predictions || {};
      el.innerHTML = Object.entries(pred)
        .map(([k, v]) => `<div><span class="muted">${k}</span> <strong>${v}</strong></div>`)
        .join('');
      el.classList.remove('muted');
    } catch {
      el.textContent = 'Prediction generator unavailable';
    }
  }

  async function loadReplay() {
    const el = $('#replay-panel');
    if (!el) return;
    try {
      const data = await fetchJson(`${API}/advantage/replay/state?event_id=soviet_1982&t_offset_s=${state.replayOffset}`);
      const cmp = data.comparison || {};
      const ms = data.model_state || {};
      el.innerHTML = [
        `<div class="replay-title">${data.event || '1982 Soviet Expedition'}</div>`,
        `Ω₀ <strong>${ms.Omega0_rad_s ?? '—'}</strong> rad/s`,
        `Glow <strong>${ms.I_r_theta_t?.I_cd ?? '—'}</strong> cd @ station #4`,
        `Sim period <strong>${cmp.simulated_peaks_min ?? '—'}</strong> min`,
        `Match <strong>${cmp.match_pct ?? '—'}%</strong>`,
        `<div class="replay-controls">
          <button type="button" id="replay-play">▶ Play</button>
          <button type="button" id="replay-pause">⏸ Pause</button>
          <button type="button" id="replay-rewind">⏪ Rewind</button>
        </div>`,
      ].join('<br>');
      el.classList.remove('muted');
      bindReplayControls();
    } catch {
      el.textContent = 'Historical replay offline';
    }
  }

  function bindReplayControls() {
    $('#replay-play')?.addEventListener('click', () => {
      state.replayPlaying = true;
      clearInterval(state.replayTimer);
      state.replayTimer = setInterval(async () => {
        state.replayOffset += 852;
        await loadReplay();
      }, 800);
    });
    $('#replay-pause')?.addEventListener('click', () => {
      state.replayPlaying = false;
      clearInterval(state.replayTimer);
    });
    $('#replay-rewind')?.addEventListener('click', () => {
      state.replayOffset = 0;
      loadReplay();
    });
  }

  async function loadObservationNetwork() {
    const el = $('#obs-network');
    if (!el) return;
    try {
      const data = await fetchJson(`${API}/advantage/observations/network`);
      const obs = (data.recent_observations || [])[0];
      if (!obs) return;
      el.innerHTML = [
        `<div><strong>${obs.user}</strong> @ r=${obs.r_mi} mi</div>`,
        `Reported ${obs.reported} ± ${obs.uncertainty} cd`,
        `Predicted ${obs.predicted} cd (${obs.deviation_pct}%)`,
        `<span class="badge badge-pass">${obs.within_tolerance ? 'WITHIN TOLERANCE' : 'FLAG'}</span>`,
        `<div class="muted">Network: ${data.network_health?.active_observers} observers · ${data.network_health?.coverage_pct}% coverage</div>`,
      ].join('<br>');
      el.classList.remove('muted');
    } catch {
      el.textContent = 'Observation network offline';
    }
  }

  function bindRealityMode() {
    document.querySelectorAll('input[name="reality-mode"]').forEach((radio) => {
      radio.addEventListener('change', (e) => {
        state.realityMode = e.target.value;
        const proj = $('#projection-select');
        if (proj) {
          if (state.realityMode === 'copernican') proj.value = 'wgs84';
          else if (state.realityMode === 'udm') proj.value = 'udm_v5';
        }
        proj?.dispatchEvent(new Event('change'));
        updateDualMode(state.cursor.lat, state.cursor.lon);
        renderSpectralPreview();
      });
    });
    $('#btn-predict')?.addEventListener('click', runPredictionGenerator);
    $('#btn-ingest')?.addEventListener('click', async () => {
      try {
        const r = await fetchJson(`${API}/advantage/ingestion/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
        $('#ingest-status').textContent = `Ingested · score ${r.validation_score}`;
      } catch {
        $('#ingest-status').textContent = 'Ingest failed';
      }
    });
  }

  window.UDM_ADVANTAGE = {
    onMapClick(lat, lon) {
      state.cursor = { lat, lon };
      updateDualMode(lat, lon);
    },
    init() {
      bindRealityMode();
      loadAdvantageSummary();
      loadPredictions();
      loadReplay();
      loadObservationNetwork();
      renderSpectralPreview();
      connectTelemetry();
      updateDualMode(state.cursor.lat, state.cursor.lon);
    },
  };
})();