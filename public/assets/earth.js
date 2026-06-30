/**
 * UDM Earth — edge-static atlas, client-side projection, zero-lag layer switches.
 */
(function () {
  const PHI_WIND = 70.55;
  const PHI_NODE = -19.45;
  const ALPHA_ANTI = 16.9;
  const KAPPA = 0.0514;
  const ORIGIN = window.EARTH_ORIGIN || window.location.origin;
  const DATA = `${ORIGIN}/data`;
  const API = `${ORIGIN}/api`;

  const $ = (s) => document.querySelector(s);

  const state = {
    manifest: null,
    layerCache: new Map(),
    currentLayer: 'star_forts',
    projectionMode: 'udm_flat',
    lstHours: 12,
    globeView: false,
    measureMode: false,
    measurePts: [],
    markers: [],
    map: null,
    layerGroup: null,
    renderGen: 0,
  };

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
      return { lat: lat, lon: lon, W: winding(lat), A: amplitude(lat), Y: masterY(lat, lst) };
    }
    const w = winding(lat);
    const phase = statorPhase(lst);
    const nodePull = (PHI_NODE - lat) * Math.abs(w) * 0.08;
    const latUdm = lat + nodePull;
    const lonUdm = lon * Math.abs(w) * (0.92 + 0.08 * phase);
    return { lat: latUdm, lon: lonUdm, W: w, A: amplitude(lat), Y: masterY(lat, lst) };
  }

  function formatLst(h) {
    const hr = Math.floor(h);
    const m = Math.round((h - hr) * 60);
    return `${String(hr).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  async function fetchJson(url) {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`${url} → ${res.status}`);
    return res.json();
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
    $('#brand-sub').textContent = `Updated ${new Date(state.manifest.built_at).toLocaleDateString()} · edge CDN`;
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
        if (!state.layerCache.has(l.id)) {
          loadLayerData(l.id).catch(() => {});
        }
      });
    };
    if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 4000 });
    else setTimeout(run, 800);
  }

  function initMap() {
    state.map = L.map('map', {
      center: [38.25, -85.76],
      zoom: 6,
      zoomControl: true,
      preferCanvas: true,
    });
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
      const m = L.circleMarker([p.lat, p.lon], {
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
      bounds.push([p.lat, p.lon]);
    }

    if (gen !== state.renderGen) return;

    $('#layer-count').textContent = `${sites.length} sites`;
    $('#status-line').textContent = 'Ready';
    if (bounds.length) {
      state.map.fitBounds(bounds, { padding: [24, 24], maxZoom: 10 });
    }
  }

  async function switchLayer(layerId) {
    state.currentLayer = layerId;
    $('#status-line').textContent = 'Switching…';
    if (!state.layerCache.has(layerId)) {
      await loadLayerData(layerId);
    }
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
      s.t ? `type: ${s.t}` : '',
      s.th ? `thread: ${s.th}` : '',
      `W(φ)=${p.W.toFixed(4)}  Y=${p.Y.toFixed(4)}`,
    ].filter(Boolean).join('\n');
    updateMetrics(s.la, s.lo, state.lstHours);
  }

  function updateMetrics(lat, lon, lst) {
    const p = projectFlat(lat, lon, lst, state.projectionMode);
    $('#m-w').textContent = p.W.toFixed(4);
    $('#m-a').textContent = p.A.toFixed(4);
    $('#m-y').textContent = p.Y.toFixed(4);
  }

  let lstTimer = null;
  function onLstInput(h) {
    state.lstHours = h;
    $('#lst-label').textContent = formatLst(h);
    clearTimeout(lstTimer);
    lstTimer = setTimeout(rerenderProjection, 40);
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
      const t = (winding(lat) + 1) / 2;
      colors.push(0.25 + 0.55 * t, 0.28, 0.45 + 0.45 * (1 - t));
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
  }

  async function boot() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('layer')) state.currentLayer = params.get('layer');

    setupOnboard();
    bindUi();
    initMap();
    try {
      await loadManifest();
      if (!(state.manifest.layers || []).some((l) => l.id === state.currentLayer)) {
        state.currentLayer = state.manifest.layers?.[0]?.id || 'star_forts';
      }
      await loadLayerData(state.currentLayer);
      renderLayer(state.currentLayer);
      prefetchLayers();
      updateMetrics(38.25, -85.76, state.lstHours);
      pollLive();
      setInterval(pollLive, 90000);
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