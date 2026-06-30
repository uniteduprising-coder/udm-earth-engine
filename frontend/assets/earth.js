/* UDM Earth — MapLibre-free Leaflet + Three.js globe */

const PHI_WIND = 70.55;
const PHI_NODE = -19.45;
const ALPHA_ANTI = 16.9;
const KAPPA = 0.0514;
const API = window.EARTH_API_BASE || '';

const $ = (s) => document.querySelector(s);

function winding(phi) {
  return Math.cos((phi - PHI_WIND) * Math.PI / 180);
}
function amplitude(phi) {
  return 0.1699 * winding(phi);
}
function statorPhase(lst) {
  return Math.cos(2 * Math.PI * (lst - ALPHA_ANTI) / 24);
}
function masterY(phi, lst) {
  return KAPPA * winding(phi) * statorPhase(lst);
}
function projectFlat(lat, lon, lst, mode) {
  if (mode === 'wgs84') return { lat_udm: lat, lon_udm: lon, W: winding(lat), A: amplitude(lat), Y: masterY(lat, lst) };
  const w = winding(lat);
  const phase = statorPhase(lst);
  const nodePull = (PHI_NODE - lat) * Math.abs(w) * 0.08;
  const latUdm = lat + nodePull;
  const lonUdm = lon * Math.abs(w) * (0.92 + 0.08 * phase);
  return { lat_udm: latUdm, lon_udm: lonUdm, W: w, A: amplitude(lat), Y: masterY(lat, lst) };
}

let map, layerGroup, measureMode = false, measurePts = [];
let globeScene, globeCamera, globeRenderer, globeAnim;
let layersMeta = [];
let currentLayer = 'star_forts';
let projectionMode = 'udm_flat';
let lstHours = 12;
let globeView = false;

function formatLst(h) {
  const hr = Math.floor(h);
  const m = Math.round((h - hr) * 60);
  return `${String(hr).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

async function api(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

function initMap() {
  map = L.map('map', { center: [38.25, -85.76], zoom: 6, zoomControl: true });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OSM &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
  layerGroup = L.layerGroup().addTo(map);
  map.on('click', onMapClick);
}

function markerColor(layerId) {
  const layer = layersMeta.find((l) => l.id === layerId);
  return layer?.color || '#38bdf8';
}

function renderGeojson(geojson, layerId) {
  layerGroup.clearLayers();
  const color = markerColor(layerId);
  const features = geojson?.features || [];
  features.forEach((f) => {
    if (f.geometry?.type !== 'Point') return;
    const props = f.properties || {};
    const rawLat = props.lat_raw ?? props.lat;
    const rawLon = props.lon_raw ?? props.lon;
    let lat = f.geometry.coordinates[1];
    let lon = f.geometry.coordinates[0];
    if (projectionMode === 'udm_flat' && rawLat != null && rawLon != null) {
      const p = projectFlat(+rawLat, +rawLon, lstHours, 'udm_flat');
      lat = p.lat_udm;
      lon = p.lon_udm;
    }
    const m = L.circleMarker([lat, lon], {
      radius: 6,
      color: '#fff',
      weight: 1,
      fillColor: color,
      fillOpacity: 0.85,
      className: 'udm-marker',
    });
    m.bindPopup(`<strong>${props.name || props.site_name || f.id}</strong><br/>W=${(props.udm?.W ?? winding(rawLat)).toFixed(3)}`);
    m.on('click', () => showSiteDetail(props, f.id));
    m.addTo(layerGroup);
  });
  $('#layer-count').textContent = `${features.length} markers · ${layerId}`;
  if (features.length) {
    const bounds = layerGroup.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.15));
  }
}

function showSiteDetail(props, id) {
  const udm = props.udm || {};
  $('#site-detail').textContent = JSON.stringify({
    id,
    name: props.name || props.site_name,
    lat_raw: props.lat_raw,
    lon_raw: props.lon_raw,
    layer: props.layer_id,
    W: udm.W,
    Y: udm.Y,
    thread: props.thread,
    structure_type: props.structure_type,
  }, null, 2);
  updateMetrics(props.lat_raw ?? props.lat ?? 38, lstHours);
}

function updateMetrics(lat, lst, lon = -85.76) {
  const p = projectFlat(lat, lon, lst, projectionMode);
  $('#m-w').textContent = p.W.toFixed(4);
  $('#m-a').textContent = p.A.toFixed(4);
  $('#m-y').textContent = p.Y.toFixed(4);
}

async function loadLayer(layerId) {
  currentLayer = layerId;
  $('#status-line').textContent = `Loading ${layerId}…`;
  try {
    const data = await api(`/v1/layer/${layerId}?lst_hours=${lstHours}&mode=${projectionMode}`);
    renderGeojson(data.geojson, layerId);
    $('#status-line').textContent = `Layer: ${layerId} · ${projectionMode}`;
  } catch (e) {
    $('#status-line').textContent = `Error: ${e.message}`;
  }
}

async function loadLayersDropdown() {
  const data = await api('/v1/layers');
  layersMeta = data.layers || [];
  const sel = $('#layer-select');
  sel.innerHTML = '';
  layersMeta.forEach((l) => {
    const opt = document.createElement('option');
    opt.value = l.id;
    opt.textContent = `${l.icon || ''} ${l.label}`.trim();
    sel.appendChild(opt);
  });
  sel.value = currentLayer;
}

async function refreshFeeds() {
  $('#feed-status').textContent = 'Refreshing…';
  try {
    await api('/v1/refresh', { method: 'POST' });
    await loadLayer(currentLayer);
    await pollFeeds();
    $('#status-line').textContent = 'Refreshed at ' + new Date().toLocaleTimeString();
  } catch (e) {
    $('#feed-status').innerHTML = `<span class="feed-err">${e.message}</span>`;
  }
}

async function pollFeeds() {
  const ids = ['sun_moon_ephemeris', 'geo_stream_bridge', 'nasa_epic_latest'];
  const lines = [];
  for (const id of ids) {
    try {
      const rec = await api(`/v1/stream/${id}`);
      const p = rec.payload || rec;
      if (id === 'sun_moon_ephemeris' && p.sun) {
        lines.push(`<div class="feed-ok">☀ Sun ${p.sun.subsolar_lat}°, ${p.sun.subsolar_lon}°</div>`);
        lines.push(`<div class="feed-ok">☽ Moon illum ${(p.moon?.illumination * 100 || 0).toFixed(0)}%</div>`);
      } else if (id === 'geo_stream_bridge') {
        const ok = Object.keys(p.feeds || {}).length;
        lines.push(`<div class="feed-ok">⚡ Geo bridge: ${ok} feeds</div>`);
      } else if (id === 'nasa_epic_latest' && p.image_url) {
        lines.push(`<div class="feed-ok">🛰 NASA EPIC loaded</div>`);
        $('#nasa-card').classList.remove('hidden');
        $('#nasa-epic-img').src = p.image_url;
      } else {
        lines.push(`<div class="feed-ok">${id}: ok</div>`);
      }
    } catch {
      lines.push(`<div class="feed-err">${id}: offline</div>`);
    }
  }
  $('#feed-status').innerHTML = lines.join('');
}

function onMapClick(e) {
  if (!measureMode) {
    updateMetrics(e.latlng.lat, lstHours);
    return;
  }
  measurePts.push(e.latlng);
  if (measurePts.length === 2) {
    const d = map.distance(measurePts[0], measurePts[1]);
    L.popup().setLatLng(measurePts[1]).setContent(`Distance: ${(d / 1000).toFixed(2)} km`).openOn(map);
    measurePts = [];
    measureMode = false;
    $('#btn-measure').textContent = '📏 Measure';
  }
}

function initGlobe() {
  const canvas = $('#globe-canvas');
  const wrap = canvas.parentElement;
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  globeScene = new THREE.Scene();
  globeCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
  globeCamera.position.set(0, 0.3, 2.8);
  globeRenderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  globeRenderer.setSize(w, h);
  const light = new THREE.DirectionalLight(0xffffff, 0.9);
  light.position.set(2, 2, 3);
  globeScene.add(light, new THREE.AmbientLight(0xffffff, 0.4));
  const geo = new THREE.SphereGeometry(1, 48, 32);
  const pos = geo.attributes.position;
  const colors = [];
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i);
    const lat = Math.asin(y) * 180 / Math.PI;
    const t = (winding(lat) + 1) / 2;
    colors.push(0.2 + 0.6 * t, 0.3 + 0.2 * (1 - Math.abs(winding(lat))), 0.5 + 0.5 * (1 - t));
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7 }));
  globeScene.add(mesh);
  const ringPts = [];
  for (let lon = 0; lon <= 360; lon += 4) {
    const phi = PHI_WIND * Math.PI / 180;
    ringPts.push(new THREE.Vector3(Math.cos(phi) * Math.cos(lon * Math.PI / 180), Math.sin(phi), Math.cos(phi) * Math.sin(lon * Math.PI / 180)));
  }
  const ring = new THREE.Line(new THREE.BufferGeometry().setFromPoints(ringPts), new THREE.LineBasicMaterial({ color: 0xf59e0b }));
  globeScene.add(ring);
  function anim() {
    globeAnim = requestAnimationFrame(anim);
    mesh.rotation.y += 0.002;
    globeRenderer.render(globeScene, globeCamera);
  }
  anim();
}

function toggleView() {
  globeView = !globeView;
  $('#map-panel').classList.toggle('hidden', globeView);
  $('#globe-panel').classList.toggle('hidden', !globeView);
  $('#btn-view').textContent = globeView ? '🗺 Map' : '🌐 Globe';
  if (globeView && !globeRenderer) initGlobe();
  setTimeout(() => map?.invalidateSize(), 100);
}

function bindUi() {
  $('#layer-select').addEventListener('change', (e) => loadLayer(e.target.value));
  $('#projection-select').addEventListener('change', (e) => {
    projectionMode = e.target.value;
    loadLayer(currentLayer);
  });
  $('#lst-slider').addEventListener('input', (e) => {
    lstHours = +e.target.value;
    $('#lst-label').textContent = formatLst(lstHours);
    loadLayer(currentLayer);
  });
  $('#btn-refresh').addEventListener('click', refreshFeeds);
  $('#btn-measure').addEventListener('click', () => {
    measureMode = !measureMode;
    measurePts = [];
    $('#btn-measure').textContent = measureMode ? '📏 Click 2 pts' : '📏 Measure';
  });
  $('#btn-view').addEventListener('click', toggleView);
}

async function boot() {
  initMap();
  bindUi();
  try {
    await loadLayersDropdown();
    await loadLayer(currentLayer);
    await pollFeeds();
    updateMetrics(38.25, lstHours);
  } catch (e) {
    $('#status-line').textContent = `Boot error: ${e.message}`;
  }
  setInterval(pollFeeds, 60000);
}

boot();