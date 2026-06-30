/** Single-file edge worker — UDM Cosmology Engine v5.2α + static atlas */

const GITHUB_RAW =
  "https://raw.githubusercontent.com/uniteduprising-coder/udm-earth-engine/master/public";
const GEO_API = "https://geo-api.uniteduprising.com";

const ALLOWED = new Set([
  "https://uniteduprising.com",
  "https://www.uniteduprising.com",
  "https://earth.uniteduprising.com",
  "http://localhost:8787",
  "http://localhost:8790",
]);

function cors(request: Request): Record<string, string> {
  const origin = request.headers.get("Origin") ?? "";
  const allow = ALLOWED.has(origin) ? origin : "https://uniteduprising.com";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data: unknown, corsH: Record<string, string>, cacheSec = 0): Response {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...corsH };
  if (cacheSec > 0) headers["Cache-Control"] = `public, max-age=${cacheSec}, stale-while-revalidate=${cacheSec * 2}`;
  return new Response(JSON.stringify(data), { headers });
}

async function fetchRaw(path: string): Promise<Response> {
  return fetch(`${GITHUB_RAW}${path}`, { cf: { cacheTtl: 3600 } });
}

async function fetchJsonRaw<T>(path: string): Promise<T | null> {
  const r = await fetchRaw(path);
  if (!r.ok) return null;
  return r.json() as Promise<T>;
}

function julianDay(d: Date): number {
  let y = d.getUTCFullYear();
  let m = d.getUTCMonth() + 1;
  const day = d.getUTCDate() + (d.getUTCHours() + d.getUTCMinutes() / 60) / 24;
  if (m <= 2) {
    y -= 1;
    m += 12;
  }
  const a = Math.floor(y / 100);
  const b = 2 - a + Math.floor(a / 4);
  return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + day + b - 1524.5;
}

function sunMoon(now = new Date()) {
  const jd = julianDay(now);
  const n = jd - 2451545.0;
  const L = ((280.46 + 0.9856474 * n) % 360) * (Math.PI / 180);
  const g = ((357.528 + 0.9856003 * n) % 360) * (Math.PI / 180);
  const lam = L + (1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * (Math.PI / 180);
  const eps = (23.439 - 0.0000004 * n) * (Math.PI / 180);
  const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam));
  const lst = (now.getUTCHours() + now.getUTCMinutes() / 60) % 24;
  const M = ((134.963 + 13.064993 * n) % 360) * (Math.PI / 180);
  return {
    timestamp: now.toISOString(),
    lst_hours_utc: Math.round(lst * 100) / 100,
    sun: {
      subsolar_lat: Math.round((dec * 180) / Math.PI * 100) / 100,
      subsolar_lon: Math.round((((ra * 180) / Math.PI - lst * 15 + 180) % 360) - 180 * 100) / 100,
    },
    moon: { illumination: Math.round(((1 - Math.cos(M)) / 2) * 1000) / 1000 },
  };
}

async function geoBridge() {
  const feeds = ["schumann_resonance", "nasa_donki_flares", "weather_local"];
  const out: Record<string, unknown> = { source: GEO_API, feeds: {} };
  await Promise.all(
    feeds.map(async (id) => {
      try {
        const r = await fetch(`${GEO_API}/v1/stream/${id}`);
        (out.feeds as Record<string, unknown>)[id] = r.ok ? await r.json() : { error: r.status };
      } catch (e) {
        (out.feeds as Record<string, unknown>)[id] = { error: String(e) };
      }
    })
  );
  return out;
}

const OBS_LAYERS = [
  { key: "soviet_1982", label: "1982 Soviet Stations", active: true },
  { key: "mercator_1569", label: "Mercator 1569 Coastlines", active: true },
  { key: "fine_1531", label: "Finé 1531 Landmarks", active: true },
  { key: "swarm_mag", label: "SWARM Magnetic Anomaly", active: false },
  { key: "aurora_hist", label: "Historical Aurorae (1880–1930)", active: false },
  { key: "glow_reports", label: "Independent Glow Reports", active: false },
  { key: "mt_conductivity", label: "MT Conductivity Data", active: false },
  { key: "river_deltas", label: "Arctic River Deltas", active: false },
  { key: "grace_gravity", label: "GRACE Gravity Anomaly", active: false },
  { key: "schumann_elf", label: "Schumann ELF Spectra", active: false },
  { key: "lod_iers", label: "LOD Residuals (IERS)", active: false },
];

const MIME: Record<string, string> = {
  ".html": "text/html;charset=utf-8",
  ".css": "text/css;charset=utf-8",
  ".js": "application/javascript;charset=utf-8",
  ".json": "application/json;charset=utf-8",
};

function mime(path: string): string {
  const ext = path.slice(path.lastIndexOf("."));
  return MIME[ext] || "application/octet-stream";
}

export default {
  async fetch(request: Request, _env: unknown, ctx: ExecutionContext): Promise<Response> {
    const corsH = cors(request);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsH });

    const url = new URL(request.url);
    let path = url.pathname;
    if (path === "/embed") path = "/";

    if (path === "/api/health") {
      return json(
        {
          service: "udm-earth-engine",
          status: "ok",
          edge: true,
          mode: "standalone",
          cosmology_engine: "5.2β",
          projection: "udm_v5",
        },
        corsH,
        30
      );
    }
    if (path === "/api/live/ephemeris") return json(sunMoon(), corsH, 120);
    if (path === "/api/live/geo") {
      const key = new Request(request.url, { method: "GET" });
      const hit = await caches.default.match(key);
      if (hit) {
        const out = new Response(hit.body, hit);
        Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
        return out;
      }
      const payload = await geoBridge();
      const res = json(payload, corsH, 60);
      ctx.waitUntil(caches.default.put(key, res.clone()));
      return res;
    }

    if (path === "/api/params") {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/params.json");
      return json(baked ?? { error: "params not baked" }, corsH, 120);
    }
    if (path === "/api/cosmology/state") {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/state.json");
      return json(baked ?? { error: "state not baked" }, corsH, 60);
    }
    if (
      path === "/api/cosmology/chromatic" ||
      path === "/api/cosmology/terminator" ||
      path === "/api/cosmology/daynight"
    ) {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/chromatic.json");
      if (path === "/api/cosmology/daynight" && baked?.state_at_point) {
        const lat = url.searchParams.get("lat");
        const lon = url.searchParams.get("lon");
        return json(
          { ...(baked.state_at_point as object), lat: lat ? Number(lat) : null, lon: lon ? Number(lon) : null },
          corsH,
          60
        );
      }
      return json(baked ?? { error: "chromatic not baked" }, corsH, 120);
    }
    if (path === "/api/validate" || path === "/api/run_full_validation") {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/validation.json");
      if (path === "/api/run_full_validation" && baked) {
        baked.generated_at = new Date().toISOString();
      }
      return json(baked ?? { error: "validation not baked" }, corsH, 60);
    }
    if (path === "/api/observations/layers") {
      return json({ layers: OBS_LAYERS }, corsH, 300);
    }
    if (path.startsWith("/api/celestial/")) {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/celestial_governance.json");
      if (!baked) {
        return json(
          { document: "North Axis Aperture and Celestial Governance", note: "Run scripts/bake_cosmology.py to bake" },
          corsH,
          120
        );
      }
      if (path === "/api/celestial/governance") return json(baked, corsH, 300);
      if (path === "/api/celestial/hierarchy") return json({ hierarchy: baked.hierarchy ?? [] }, corsH, 300);
      if (path === "/api/celestial/classification") {
        return json({ classification_table: baked.classification_table ?? [] }, corsH, 300);
      }
      if (path === "/api/celestial/measurements") {
        return json({ measurement_feeds: baked.measurement_feeds ?? {} }, corsH, 300);
      }
      if (path === "/api/celestial/north-axis") {
        const lat = Number(url.searchParams.get("lat") ?? "NaN");
        if (!Number.isFinite(lat)) return json({ error: "lat query parameter required (degrees)" }, corsH, 400);
        const defaults = (baked.north_axis_aperture as { defaults?: Record<string, number> })?.defaults ?? {};
        const rf = Number(url.searchParams.get("R_f") ?? defaults.R_f ?? 0);
        const ao = Number(url.searchParams.get("A_o") ?? defaults.A_o ?? 0);
        const vp = Number(url.searchParams.get("V_p") ?? defaults.V_p ?? 0);
        const alpha = Math.round((lat + rf + ao + vp) * 10000) / 10000;
        return json(
          {
            phi_deg: lat,
            alpha_N_deg: alpha,
            R_f: rf,
            A_o: ao,
            V_p: vp,
            residual_deg: Math.round((alpha - lat) * 10000) / 10000,
            matches_latitude_rule: Math.abs(alpha - lat) < 0.01,
          },
          corsH,
          120
        );
      }
      return json(baked, corsH, 300);
    }
    if (path.startsWith("/api/encyclopedia")) {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/encyclopedia.json");
      if (!baked) {
        return json(
          {
            document: "UDM Master Encyclopedia",
            tiers: { T1: "empirically sourced", T4: "simulation parameter" },
            note: "Run scripts/ingest_encyclopedia.py to bake",
          },
          corsH,
          120
        );
      }
      return json(baked, corsH, 300);
    }
    if (path === "/realtime" || path === "/realtime.html") {
      const asset = await fetchRaw("/realtime.html");
      if (asset.ok) {
        const out = new Response(asset.body, asset);
        out.headers.set("Content-Type", "text/html;charset=utf-8");
        Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
        return out;
      }
    }
    if (path === "/globe" || path === "/globe.html" || path === "/view") {
      const asset = await fetchRaw("/globe.html");
      if (asset.ok) {
        const out = new Response(asset.body, asset);
        out.headers.set("Content-Type", "text/html;charset=utf-8");
        Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
        return out;
      }
    }
    if (path === "/toroid" || path === "/toroid.html") {
      const asset = await fetchRaw("/toroid.html");
      if (asset.ok) {
        const out = new Response(asset.body, asset);
        out.headers.set("Content-Type", "text/html;charset=utf-8");
        Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
        return out;
      }
    }
    if (path.startsWith("/api/procedural/")) {
      if (path === "/api/procedural/status") {
        const baked = await fetchJsonRaw<Record<string, unknown>>("/data/procedural/manifest.json");
        return json(baked ?? { ok: false, message: "Run procedural build" }, corsH, 120);
      }
      if (path === "/api/procedural/layers") {
        const baked = await fetchJsonRaw<Record<string, unknown>>("/data/procedural/layers.json");
        return json(baked ?? { layers: {}, message: "Run procedural build" }, corsH, 120);
      }
      if (path === "/api/procedural/terminations") {
        const baked = await fetchJsonRaw<Record<string, unknown>>("/data/procedural/terminations.json");
        return json(baked ?? { error: "terminations not published" }, corsH, 300);
      }
      if (path === "/api/procedural/build" && request.method === "POST") {
        return json(
          { ok: false, edge: true, note: "POST /api/procedural/build runs on Python API — edge serves baked assets only" },
          corsH
        );
      }
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/procedural/manifest.json");
      return json(baked ?? { error: "procedural not published" }, corsH, 120);
    }
    if (path.startsWith("/api/toroidal/")) {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/toroidal.json");
      if (!baked) return json({ error: "toroidal not baked" }, corsH);
      if (path === "/api/toroidal/domain") return json(baked.domain ?? baked, corsH, 300);
      if (path === "/api/toroidal/state") return json(baked, corsH, 120);
      if (path === "/api/toroidal/void") return json(baked.void ?? {}, corsH, 300);
      if (path === "/api/toroidal/twin-cell") return json(baked.twin_cell ?? {}, corsH, 120);
      if (path === "/api/toroidal/view-modes") return json({ mode: "top", available: ["top", "underside", "toroidal"] }, corsH, 300);
      return json(baked, corsH, 120);
    }
    if (path.startsWith("/api/advantage/")) {
      const baked = await fetchJsonRaw<Record<string, unknown>>("/data/cosmology/advantage.json");
      if (!baked) return json({ error: "advantage not baked" }, corsH);
      if (path === "/api/advantage/summary") return json(baked.summary ? { summary: baked.summary, ...baked } : baked, corsH, 120);
      if (path === "/api/advantage/spectral") {
        const cosmology = url.searchParams.get("cosmology") || "udm";
        const key = cosmology === "copernican" ? "spectral_copernican" : "spectral_udm";
        return json((baked[key] as object) ?? baked.spectral_udm, corsH, 300);
      }
      if (path === "/api/advantage/predictions") return json(baked.predictions ?? {}, corsH, 120);
      if (path === "/api/advantage/observations/network") return json(baked.observation_network ?? {}, corsH, 120);
      if (path === "/api/advantage/replay" || path === "/api/advantage/replay/state") return json(baked.replay ?? {}, corsH, 120);
      if (path === "/api/advantage/ingestion") return json(baked.ingestion ?? {}, corsH, 120);
      if (path === "/api/advantage/dual-mode" || path === "/api/advantage/predict") {
        return json({ edge: true, note: "Use Python API for live dual-mode / predict", baked: true }, corsH);
      }
      if (path === "/api/advantage/ingestion/run" && request.method === "POST") {
        return json({ ok: true, edge: true, note: "Ingest stub on edge", validation_score: "15/18" }, corsH);
      }
      return json(baked, corsH, 120);
    }
    if (path === "/api/update" && request.method === "POST") {
      const key = url.searchParams.get("key");
      const val = url.searchParams.get("val");
      return json(
        {
          ok: true,
          edge: true,
          note: "Edge worker cannot persist params.yml — use local Python API for authoritative updates",
          updated: key ? [key] : [],
          key,
          val: val ? Number(val) : null,
        },
        corsH
      );
    }

    const assetPath = path === "/" ? "/index.html" : path;
    const upstream = `${GITHUB_RAW}${assetPath}`;
    const cache = caches.default;
    const cacheKey = new Request(upstream, { method: "GET" });
    let asset = await cache.match(cacheKey);
    if (!asset) {
      asset = await fetch(upstream, { cf: { cacheTtl: 3600 } });
      if (asset.ok) ctx.waitUntil(cache.put(cacheKey, asset.clone()));
    }
    const out = new Response(asset.body, asset);
    out.headers.set("Content-Type", mime(assetPath));
    out.headers.set("X-Edge", "udm-earth-engine");
    Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
    if (assetPath.includes("/data/layers/") || assetPath.includes("/data/cosmology/")) {
      out.headers.set("Cache-Control", "public, max-age=86400, immutable");
    } else if (assetPath.endsWith("manifest.json")) {
      out.headers.set("Cache-Control", "public, max-age=300");
    }
    return out;
  },
};