import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const MI = 0.01;
const $ = (id) => document.getElementById(id);

let scene, camera, renderer, controls, root;
let polarDisk, proceduralLayer, geocolorLayer, belowCell;
let overlayMeshes = {};
let underside = false;

async function fetchJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

function polarDiskGeometry(radius, segments = 128) {
  const geo = new THREE.CircleGeometry(radius, segments);
  const uv = geo.attributes.uv;
  const pos = geo.attributes.position;
  for (let i = 0; i < uv.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const rho = Math.min(1, Math.hypot(x, z) / radius);
    const theta = Math.atan2(x, -z);
    uv.setXY(
      i,
      0.5 + 0.5 * rho * Math.sin(theta),
      0.5 - 0.5 * rho * Math.cos(theta),
    );
  }
  return geo;
}

function makeTexturedLayer(url, radius, opacity = 1, renderOrder = 2) {
  const tex = new THREE.TextureLoader().load(url + "?t=" + Date.now());
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(polarDiskGeometry(radius), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.renderOrder = renderOrder;
  return mesh;
}

function buildToroidGroup(params, layerCatalog) {
  const g = new THREE.Group();
  const rDisk = params.R_disk * MI;
  const rBase = params.r_base * MI;
  const rIso = params.r_iso * MI;
  const aIso = params.a_iso * MI;
  const zT = -Math.abs(params.z_T) * MI;
  const diskR = rBase * 0.98;

  const rim = new THREE.Mesh(
    new THREE.TorusGeometry(rDisk, 0.08, 8, 64),
    new THREE.MeshStandardMaterial({ color: 0x223355, wireframe: true, transparent: true, opacity: 0.35 }),
  );
  rim.rotation.x = Math.PI / 2;
  g.add(rim);

  const upperDome = new THREE.Mesh(
    new THREE.SphereGeometry(rBase, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x1a2844, transparent: true, opacity: 0.35, side: THREE.DoubleSide }),
  );
  g.add(upperDome);

  const plane = new THREE.Mesh(
    new THREE.CircleGeometry(rBase, 64),
    new THREE.MeshStandardMaterial({ color: 0x1a2030, transparent: true, opacity: 0.25, side: THREE.DoubleSide }),
  );
  plane.rotation.x = -Math.PI / 2;
  g.add(plane);

  const rupes = new THREE.Mesh(
    new THREE.CylinderGeometry(0.15, 0.22, 0.5, 8),
    new THREE.MeshStandardMaterial({ color: 0x0a0810, emissive: 0x222244 }),
  );
  g.add(rupes);

  for (let i = 0; i < 4; i++) {
    const ang = Math.PI / 4 + i * Math.PI / 2;
    const isl = new THREE.Mesh(
      new THREE.SphereGeometry(aIso, 12, 12),
      new THREE.MeshStandardMaterial({ color: 0x7a8a9a, emissive: 0x111822 }),
    );
    isl.position.set(Math.cos(ang) * rIso, 0.15, Math.sin(ang) * rIso);
    g.add(isl);
  }

  polarDisk = new THREE.Group();
  polarDisk.position.y = 0.03;

  proceduralLayer = makeTexturedLayer("/data/procedural/polar.png", diskR, 1.0, 1);
  const geoUrl = layerCatalog?.layers?.geocolor?.ok
    ? "/data/procedural/layers/geocolor.png"
    : "/data/procedural/composite.png";
  geocolorLayer = makeTexturedLayer(geoUrl, diskR, 0.95, 2);

  polarDisk.add(proceduralLayer);
  polarDisk.add(geocolorLayer);

  const layerIds = ["thermal", "weather", "ocean", "jets"];
  layerIds.forEach((id, idx) => {
    const info = layerCatalog?.layers?.[id];
    const url = info?.isolated_url || `/data/procedural/layers/${id}_isolated.png`;
    const mesh = makeTexturedLayer(url, diskR, 0.0, 3 + idx);
    mesh.visible = false;
    overlayMeshes[id] = mesh;
    polarDisk.add(mesh);
  });

  g.add(polarDisk);

  belowCell = new THREE.Mesh(
    new THREE.SphereGeometry(rBase * 0.85, 48, 24, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x0d1828, transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
  );
  belowCell.position.y = zT * 0.15;
  belowCell.rotation.x = Math.PI;
  g.add(belowCell);

  const flowMat = new THREE.MeshBasicMaterial({ color: 0x44ffaa });
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    const arr = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.5, 6), flowMat);
    arr.position.set(Math.cos(a) * rBase * 0.6, 0.35, Math.sin(a) * rBase * 0.6);
    arr.lookAt(0, 0.6, 0);
    g.add(arr);
  }

  return g;
}

function setView(mode) {
  if (!camera || !controls) return;
  underside = mode === "underside";
  const r = 45;
  if (mode === "polar" || mode === "underside") {
    camera.position.set(0, underside ? -r : r, 0.01);
    controls.target.set(0, 0, 0);
  } else {
    camera.position.set(r * 1.2, 8, r * 0.8);
    controls.target.set(0, -5, 0);
  }
  if (polarDisk) polarDisk.visible = !underside;
  if (belowCell) belowCell.visible = underside || mode === "profile" || mode === "cross";
  controls.update();
  $("td-status").textContent = underside
    ? "Below-cell outflow (Q_b < 0) — observational layers hidden"
    : `View: ${mode} — NASA overlays active on continental belt`;
}

function initThree() {
  const wrap = $("td-canvas-wrap");
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a0f);
  camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 500);
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.sortObjects = true;
  wrap.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  scene.add(new THREE.AmbientLight(0xffffff, 0.65));
  const pl = new THREE.PointLight(0xaaccff, 1.4);
  pl.position.set(20, 30, 20);
  scene.add(pl);
  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
  (function loop() {
    requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  })();
}

function bindLayerControls() {
  $("ly-procedural")?.addEventListener("change", (e) => {
    if (proceduralLayer) proceduralLayer.visible = e.target.checked;
  });
  $("ly-geocolor")?.addEventListener("change", (e) => {
    if (geocolorLayer) geocolorLayer.visible = e.target.checked;
  });

  document.querySelectorAll("[data-layer]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const id = cb.dataset.layer;
      if (id === "imf") {
        if (geocolorLayer && !underside) {
          geocolorLayer.material.color.set(cb.checked ? 0xffffff : 0xffffff);
        }
        return;
      }
      const mesh = overlayMeshes[id];
      if (mesh) {
        mesh.visible = cb.checked && !underside;
        const slider = document.querySelector(`[data-opacity="${id}"]`);
        if (slider) mesh.material.opacity = cb.checked ? slider.value / 100 : 0;
      }
    });
  });

  document.querySelectorAll("[data-opacity]").forEach((sl) => {
    sl.addEventListener("input", () => {
      const id = sl.dataset.opacity;
      const mesh = overlayMeshes[id];
      const cb = document.querySelector(`[data-layer="${id}"]`);
      if (mesh && cb?.checked) mesh.material.opacity = sl.value / 100;
    });
  });
}

async function main() {
  initThree();
  $("td-menu")?.addEventListener("click", () => $("td-panel").classList.toggle("open"));

  let params = {};
  let layerCatalog = {};
  try {
    const p = await fetchJson("/data/cosmology/params.json");
    params = p.params || p;
  } catch {
    params = { R_disk: 12500, z_max: 700, z_T: 3200, r_base: 3200, r_iso: 57.384, a_iso: 0.45 };
  }
  try {
    layerCatalog = await fetchJson("/api/procedural/layers");
  } catch {
    layerCatalog = {};
  }

  root = buildToroidGroup(params, layerCatalog);
  scene.add(root);
  setView("polar");
  bindLayerControls();

  try {
    const terms = await fetchJson("/api/procedural/terminations");
    const a = terms.anchors || {};
    const layers = layerCatalog.layers || {};
    const okLayers = Object.values(layers).filter((l) => l.ok).map((l) => l.id).join(", ") || "none";
    $("td-scale").textContent = [
      `km/px: ${a.km_per_px}`,
      `NASA layers: ${okLayers}`,
      layerCatalog.imf?.ok ? `Bz: ${layerCatalog.imf.bz_gsm_nT} nT` : "",
    ].filter(Boolean).join("\n");
    $("td-terms").textContent = (terms.features || [])
      .filter((f) => /island|rupes|equator|arctic/.test(f.name))
      .map((f) => `${f.name}: ${f.px_from_center}px`)
      .join("\n");
  } catch (e) {
    $("td-terms").textContent = String(e);
  }

  document.querySelectorAll("[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.dataset.view));
  });

  $("td-build")?.addEventListener("click", async () => {
    $("td-status").textContent = "Fetching NASA GIBS layers + rebuilding…";
    try {
      const r = await fetch("/api/procedural/build?nasa=true", { method: "POST" });
      if (!r.ok) throw new Error(r.status);
      location.reload();
    } catch (e) {
      $("td-status").textContent = `Build failed: ${e}`;
    }
  });

  $("td-status").textContent = "Ready — toggle continents + observational filters";
}

main();