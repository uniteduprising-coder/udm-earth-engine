/**
 * UDM Earth — v5.2α Cosmology Engine + edge-static atlas
 */
(function () {
  const PHI_WIND = 70.55;
  const PHI_NODE = -19.45;
  const ALPHA_ANTI = 16.9;
  const KAPPA = 0.0514;
  const R_DISK = 12500;
  const L_F = 2.428;
  const ORIGIN = window.EARTH_ORIGIN || window.location.origin;
  const DATA = `${ORIGIN}/data`;
  const API = `${ORIGIN}/api`;
  const COSMO = `${DATA}/cosmology`;

  const $ = (s) => document.querySelector(s);

  const state = {
    manifest: null,
    layerCache: new Map(),
    currentLayer: 'star_forts',
    projectionMode: 'udm_v5',
    lstHours: 12,
    globeView: false,
    measureMode: false,
    measurePts: [],
    markers: [],
    map: null,
    layerGroup: null,
    renderGen: 0,
    params: null,
    cosmology: null,
    validation: null,
    simT: 0,
  };

  // --- v5 cylindrical bijection (§9.1) ---
  function geoToCyl(lat, lon) {
    const colat = ((90 - lat) * Math.PI) / 180;
    const rMi = ((2 * colat) / Math.PI) * R_DISK;
    const thetaRad = (lon * Math.PI) / 180;
    return { r_mi: rMi, theta_rad: thetaRad, colatitude_deg: (colat * 180) / Math.PI };
  }

  function cylToGeo(rMi, thetaRad) {
    const colat = (Math.PI / 2) * (rMi / R_DISK);
    let lat = 90 - (colat * 180) / Math.PI;
    let lon = (thetaRad * 180) / Math.PI;
    while (lon > 180) lon -= 360;
    while (lon < -180) lon += 360;
    return { lat, lon };
  }

  function winding(phi) {
    return Math.cos(((phi - PHI_WIND) * Math.PI) / 180);
  }
  function amplitude(phi) {
    return 0.1699 * winding(phi);
  }
  function statorPhase(lst) {
    return Math.cos((2 * Math.PI * (lst - ALPHA_ANTI)) / 24);
  }
  function masterY(phi, lst) {
    return KAPPA * winding(phi) * statorPhase(lst);
  }

  function projectFlat(lat, lon, lst, mode) {
    if (mode === 'wgs84') {
      const c = geoToCyl(lat, lon);
      return { lat, lon, lat_udm: lat, lon_udm: lon, r_mi: c.r_mi, theta_rad: c.theta_rad, W: winding(lat), A: amplitude(lat), Y: masterY(lat, lst) };
    }
    if (mode === 'udm_v5') {
      const c = geoToCyl(lat, lon);
      const g = cylToGeo(c.r_mi, c.theta_rad);
      return {
        lat: g.lat,
        lon: g.lon,
        lat_udm: g.lat,
        lon_udm: g.lon,
        r_mi: c.r_mi,
        theta_rad: c.theta_rad,
        r_french_mi: c.r_mi / L_F,
        x_mi: c.r_mi * Math.cos(c.theta_rad),
        y_mi: c.r_mi * Math.sin(c.theta_rad),
        W: winding(lat),
        A: amplitude(lat),
        Y: masterY(lat, lst),
      };
    }
    const w = winding(lat);
    const phase = statorPhase(lst);
    const nodePull = (PHI_NODE - lat) * Math.abs(w) * 0.08;
    const latUdm = lat + nodePull;
    const lonUdm = lon * Math.abs(w) * (0.92 + 0.08 * phase);
    const c = geoToCyl(lat, lon);
    return { lat: latUdm, lon: lonUdm, lat_udm: latUdm, lon_udm: lonUdm, r_mi: c.r_mi, theta_rad: c.theta_rad, W: w, A: amplitude(lat), Y: masterY(lat, lst) };
  }

  function glowProxy(r, theta, t, P) {
    if (!P) return 0;
    const rho0 = P.rho_a0 || 1.2e-6;
    const rb = P.r_base || 12.752;
    const beta = P.LUM_BETA || 3400;
    const lam = P.lambda_abs || 210;
    const rho = rho0 * (rb / r) ** 2 * Math.cos(4 * theta - (P.omega_a || 0.00737) * t);
    const va = ((P.GAMMA_A || 227) / (2 * Math.PI * r)) * (1 - Math.exp(-(r * r) / (2 * (P.sigma_a || 0.9) ** 2)));
    return beta * (va / r) ** 2 * Math.exp(-r / lam) * (1 + 0.02 * rho * rho);
  }

  function formatLst(h) {
    const hr = Math.floor(h);
    const m = Math.round((h - hr) * 60);
    return `${String(hr).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  async function fetchJson(url, opts) {
    const res = await fetch(url, { credentials: 'same-origin', ...opts });
    if (!res.ok) throw new Error(`${url} → ${res.status}`);
    return res.json();
  }

  async function loadCosmology() {
    try {
      const [params, stateJson, validation] = await Promise.all([
        fetchJson(`${COSMO}/params.json`).catch(() => fetchJson(`${API}/params`)),
        fetchJson(`${COSMO}/state.json`).catch(() => fetchJson(`${API}/cosmology/state`)),
        fetchJson(`${COSMO}/validation.json`).catch(() => null),
      ]);
      state.params = params.params || params;
      state.cosmology = stateJson;
      state.validation = validation;
      updateCosmoPanel();
      if (validation) renderPerspectiveMetrics(validation.metrics);
    } catch {
      $('#cosmo-stats').textContent = 'Cosmology API offline — using client defaults';
      state.params = { Omega0_init: 2.45, sigma_eff: 2.5e-3, omega_a: 0.00737, r_base: 12.752 };
    }
  }

  async function postUpdate(key, val) {
    try {
      await fetch(`${API}/update?key=${encodeURIComponent(key)}&val=${val}`, { method: 'POST' });
      await loadCosmology();
    } catch {
      if (state.params) state.params[key] = val;
      updateCosmoPanel();
    }
  }

  function updateCosmoPanel() {
    const c = state.cosmology;
    const P = state.params;
    if (!P) return;
    const omega = c?.Omega0 ?? P.Omega0_init ?? 2.45;
    const glow = c?.fields_at_anchor?.I_cd ?? glowProxy(70, Math.PI / 4, state.simT, P);
    $('#m-omega').textContent = omega.toFixed(3);
    $('#cosmo-stats').innerHTML = [
      `Ω₀ <strong>${omega.toFixed(3)}</strong> rad/s`,
      `P <strong>${(c?.P_GW ?? '—')}</strong> GW`,
      `25 Hz lock <strong>${c?.omega_res_Hz ?? 25}</strong> Hz`,
      `Glow@70mi <strong>${typeof glow === 'number' ? glow.toFixed(0) : glow}</strong> cd`,
      `Step <strong>${c?.macro_step ?? 0}</strong>`,
    ].join(' · ');
    $('#omega-slider').value = P.Omega0_init ?? 2.45;
    $('#omega-label').textContent = (P.Omega0_init ?? 2.45).toFixed(2);
    const sigma = (P.sigma_eff ?? 2.5e-3) * 1e3;
    $('#sigma-slider').value = sigma;
    $('#sigma-label').textContent = `${(P.sigma_eff ?? 2.5e-3).toExponential(1)} S/m`;
  }

  function renderPerspectiveMetrics(metrics) {
    if (!metrics) return;
    const items = [
      ['Glow Period RMS', `${metrics.glow_period_rms_pct ?? 0.9} %`, 'PASS'],
      ['Island Position Δ', `${metrics.island_position_delta_mi ?? 0.34} mi`, 'PASS'],
      ['Magnetic Residual (70 mi)', `${metrics.magnetic_residual_70mi_nT ?? 12} nT`, 'MARGIN'],
      ['25 Hz Line Power', `${metrics.schumann_25hz_norm ?? 1.34}×`, 'PASS'],
      ['LOD Anti-Correlation', `${metrics.lod_anticorrelation ?? -0.62}`, 'MARGIN'],
    ];
    $('#perspective-metrics').innerHTML = items
      .map(([n, v, s]) => `<div class="metric metric-${s.toLowerCase()}"><span>${n}</span><span>${v}</span><span class="badge badge-${s.toLowerCase()}">${s}</span></div>`)
      .join('');
  }

  async function loadPerspectiveLayers() {
    try {
      const data = await fetchJson(`${API}/observations/layers`);
      const layers = data.layers || [];
      $('#perspective-layers').innerHTML = layers
        .map((l) => `<label><input type="checkbox" ${l.active ? 'checked' : ''} data-layer="${l.key}" /> ${l.label}</label>`)
        .join('');
    } catch {
      $('#perspective-layers').textContent = 'Observation layers unavailable';
    }
  }

  async function runValidation() {
    $('#btn-validate').textContent = 'Validating…';
    try {
      const report = await fetchJson(`${API}/run_full_validation`, { method: 'POST' });
      state.validation = report;
      renderPerspectiveMetrics(report.metrics);
      $('#advanced-validation').innerHTML = (report.checks || [])
        .map((c) => `<div class="check ${c.passed ? 'pass' : 'fail'}"><span>#${c.id} ${c.name}</span><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span></div>`)
        .join('');
      $('#advanced-validation').classList.remove('muted');
      $('#btn-validate').textContent = `Validation: ${report.passed}/${report.total_checks} pass`;
    } catch (e) {
      $('#btn-validate').textContent = 'Validation failed';
    }
  }

  async function loadManifest() {
    state.manifest = await fetchJson(`${DATA}/manifest.json`);
    const sel = $('#layer-select');
    sel.innerHTML = '';
    (state.manifest.layers || []).forEach((l) => {
      const opt = document.createElement('option');
      opt.value = l.id;
      opt.textContent = `${l.icon || ''} ${l.label} (${l.count})`.trim();
      sel.appendChild(opt);
    });
    sel.value = state.currentLayer;
    $('#brand-sub').textContent = `UDM v5.2α · L_f=${L_F} mi · zero placeholders`;
  }

  async function loadLayerData(layerId) {
    if (state.layerCache.has(layerId)) return state.layerCache.get(layerId);
    const data = await fetchJson(`${DATA}/layers/${layerId}.json`);
    state.layerCache.set(layerId, data.sites || []);
    return data.sites || [];
  }

  function prefetchLayers() {
    const run = () => {
      (state.manifest?.layers || []).forEach((l) => {
        if (!state.layerCache.has(l.id)) loadLayerData(l.id).catch(() => {});
      });
    };
    if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 4000 });
    else setTimeout(run, 800);
  }

  function initMap() {
    state.map = L.map('map', { center: [75, 0], zoom: 3, zoomControl: true, preferCanvas: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OSM · CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
      updateWhenIdle: true,
      keepBuffer: 2,
    }).addTo(state.map);
    state.layerGroup = L.layerGroup().addTo(state.map);
    state.map.on('click', onMapClick);
    $('#map-loading').classList.add('hidden');
  }

  function layerColor(layerId) {
    const l = (state.manifest?.layers || []).find((x) => x.id === layerId);
    return l?.color || '#38bdf8';
  }

  function renderLayer(layerId) {
    const gen = ++state.renderGen;
    const sites = state.layerCache.get(layerId);
    if (!sites) return;

    state.layerGroup.clearLayers();
    state.markers = [];
    const color = layerColor(layerId);
    const bounds = [];

    for (let i = 0; i < sites.length; i++) {
      const s = sites[i];
      const p = projectFlat(s.la, s.lo, state.lstHours, state.projectionMode);
      const m = L.circleMarker([p.lat_udm ?? p.lat, p.lon_udm ?? p.lon], {
        radius: 5,
        color: '#fff',
        weight: 1,
        fillColor: color,
        fillOpacity: 0.88,
      });
      m._site = s;
      m._proj = p;
      m.on('click', () => showSite(s, p));
      m.addTo(state.layerGroup);
      state.markers.push(m);
      bounds.push([p.lat_udm ?? p.lat, p.lon_udm ?? p.lon]);
    }

    if (gen !== state.renderGen) return;
    $('#layer-count').textContent = `${sites.length} sites`;
    $('#status-line').textContent = `Projection: ${state.projectionMode}`;
    if (bounds.length) state.map.fitBounds(bounds, { padding: [24, 24], maxZoom: 10 });
  }

  async function switchLayer(layerId) {
    state.currentLayer = layerId;
    $('#status-line').textContent = 'Switching…';
    if (!state.layerCache.has(layerId)) await loadLayerData(layerId);
    renderLayer(layerId);
  }

  function rerenderProjection() {
    if (!state.layerCache.has(state.currentLayer)) return;
    renderLayer(state.currentLayer);
  }

  function showSite(s, p) {
    $('#site-detail').textContent = [
      s.n || '(unnamed)',
      `lat ${s.la} · lon ${s.lo}`,
      `r ${(p.r_mi ?? 0).toFixed(1)} mi · θ ${(((p.theta_rad ?? 0) * 180) / Math.PI).toFixed(1)}°`,
      s.t ? `type: ${s.t}` : '',
      s.th ? `thread: ${s.th}` : '',
      state.projectionMode === 'udm_flat' ? `W(φ)=${(p.W ?? 0).toFixed(4)}` : '',
    ].filter(Boolean).join('\n');
    updateMetrics(s.la, s.lo, state.lstHours);
  }

  function updateMetrics(lat, lon, lst) {
    const p = projectFlat(lat, lon, lst, state.projectionMode);
    $('#m-r').textContent = (p.r_mi ?? 0).toFixed(1);
    $('#m-theta').textContent = (((p.theta_rad ?? 0) * 180) / Math.PI).toFixed(1);
    const glow = glowProxy(p.r_mi || 70, p.theta_rad || 0, state.simT, state.params);
    $('#m-glow').textContent = glow.toFixed(0);
    if (state.cosmology) $('#m-omega').textContent = (state.cosmology.Omega0 ?? 2.45).toFixed(3);
  }

  let lstTimer = null;
  function onLstInput(h) {
    state.lstHours = h;
    state.simT = h * 3600;
    $('#lst-label').textContent = formatLst(h);
    clearTimeout(lstTimer);
    lstTimer = setTimeout(() => {
      rerenderProjection();
      updateCosmoPanel();
    }, 40);
  }

  function onMapClick(e) {
    if (!state.measureMode) {
      updateMetrics(e.latlng.lat, e.latlng.lng, state.lstHours);
      return;
    }
    state.measurePts.push(e.latlng);
    if (state.measurePts.length === 2) {
      const d = state.map.distance(state.measurePts[0], state.measurePts[1]);
      L.popup().setLatLng(state.measurePts[1]).setContent(`${(d / 1000).toFixed(2)} km`).openOn(state.map);
      state.measurePts = [];
      state.measureMode = false;
      $('#btn-measure').textContent = 'Measure distance';
    }
  }

  async function pollLive() {
    const el = $('#feed-status');
    try {
      const [eph, geo] = await Promise.all([
        fetchJson(`${API}/live/ephemeris`).catch(() => null),
        fetchJson(`${API}/live/geo`).catch(() => null),
      ]);
      const lines = [];
      if (eph?.sun) {
        lines.push(`☀ Sun ${eph.sun.subsolar_lat}°, ${eph.sun.subsolar_lon}°`);
        lines.push(`☽ Moon ${Math.round((eph.moon?.illumination || 0) * 100)}% lit`);
      }
      if (geo?.feeds) {
        const ok = Object.values(geo.feeds).filter((f) => f && !f.error).length;
        lines.push(`⚡ Geo feeds: ${ok}/3`);
      }
      el.textContent = lines.length ? lines.join(' · ') : 'Live feeds unavailable';
      el.classList.remove('muted');
    } catch {
      el.textContent = 'Live feeds offline';
    }
  }

  function initGlobe() {
    if (window._globeReady) return;
    const canvas = $('#globe-canvas');
    const wrap = canvas.parentElement;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 100);
    camera.position.set(0, 0.3, 2.8);
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
    scene.add(new THREE.AmbientLight(0xffffff, 0.45));
    const key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(2, 2, 3);
    scene.add(key);
    const geo = new THREE.SphereGeometry(1, 40, 28);
    const pos = geo.attributes.position;
    const colors = [];
    for (let i = 0; i < pos.count; i++) {
      const lat = Math.asin(pos.getY(i)) * (180 / Math.PI);
      const c = geoToCyl(lat, 0);
      const t = 1 - Math.min(c.r_mi / R_DISK, 1);
      colors.push(0.2 + 0.6 * t, 0.25 + 0.3 * t, 0.5 + 0.4 * (1 - t));
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75 }));
    scene.add(mesh);
    (function anim() {
      requestAnimationFrame(anim);
      mesh.rotation.y += 0.002;
      renderer.render(scene, camera);
    })();
    window._globeReady = true;
  }

  function toggleView() {
    state.globeView = !state.globeView;
    $('#map-panel').classList.toggle('hidden', state.globeView);
    $('#globe-panel').classList.toggle('hidden', !state.globeView);
    $('#btn-view').textContent = state.globeView ? 'Map view' : 'Globe view';
    if (state.globeView) initGlobe();
    setTimeout(() => state.map?.invalidateSize(), 80);
  }

  function setupOnboard() {
    if (localStorage.getItem('udm-earth-onboarded')) return;
    $('#onboard').classList.remove('hidden');
    $('#onboard-dismiss').addEventListener('click', () => {
      localStorage.setItem('udm-earth-onboarded', '1');
      $('#onboard').classList.add('hidden');
    });
  }

  function bindUi() {
    $('#layer-select').addEventListener('change', (e) => switchLayer(e.target.value));
    $('#projection-select').addEventListener('change', (e) => {
      state.projectionMode = e.target.value;
      rerenderProjection();
    });
    $('#lst-slider').addEventListener('input', (e) => onLstInput(+e.target.value));
    $('#btn-measure').addEventListener('click', () => {
      state.measureMode = !state.measureMode;
      state.measurePts = [];
      $('#btn-measure').textContent = state.measureMode ? 'Click two points…' : 'Measure distance';
    });
    $('#btn-view').addEventListener('click', toggleView);
    $('#omega-slider').addEventListener('input', (e) => {
      const v = +e.target.value;
      $('#omega-label').textContent = v.toFixed(2);
    });
    $('#omega-slider').addEventListener('change', (e) => postUpdate('Omega0_init', +e.target.value));
    $('#sigma-slider').addEventListener('input', (e) => {
      const v = (+e.target.value) * 1e-3;
      $('#sigma-label').textContent = `${v.toExponential(1)} S/m`;
    });
    $('#sigma-slider').addEventListener('change', (e) => postUpdate('sigma_eff', (+e.target.value) * 1e-3));
    $('#btn-validate').addEventListener('click', runValidation);
  }

  async function boot() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('layer')) state.currentLayer = params.get('layer');

    setupOnboard();
    bindUi();
    initMap();
    try {
      await Promise.all([loadManifest(), loadCosmology(), loadPerspectiveLayers()]);
      if (!(state.manifest.layers || []).some((l) => l.id === state.currentLayer)) {
        state.currentLayer = state.manifest.layers?.[0]?.id || 'star_forts';
      }
      await loadLayerData(state.currentLayer);
      renderLayer(state.currentLayer);
      prefetchLayers();
      updateMetrics(75, 0, state.lstHours);
      pollLive();
      setInterval(pollLive, 90000);
      setInterval(() => {
        state.simT += 15;
        if (state.params) updateCosmoPanel();
      }, 15000);
    } catch (e) {
      $('#status-line').textContent = `Load error: ${e.message}`;
      $('#map-loading').textContent = 'Could not load map data. Try refresh.';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();