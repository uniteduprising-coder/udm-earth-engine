// worker/src/standalone.ts
var GITHUB_RAW = "https://raw.githubusercontent.com/uniteduprising-coder/udm-earth-engine/master/public";
var GEO_API = "https://geo-api.uniteduprising.com";
var ALLOWED = /* @__PURE__ */ new Set([
  "https://uniteduprising.com",
  "https://www.uniteduprising.com",
  "https://earth.uniteduprising.com",
  "http://localhost:8787",
  "http://localhost:8790"
]);
function cors(request) {
  const origin = request.headers.get("Origin") ?? "";
  const allow = ALLOWED.has(origin) ? origin : "https://uniteduprising.com";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  };
}
function json(data, corsH, cacheSec = 0) {
  const headers = { "Content-Type": "application/json", ...corsH };
  if (cacheSec > 0)
    headers["Cache-Control"] = `public, max-age=${cacheSec}, stale-while-revalidate=${cacheSec * 2}`;
  return new Response(JSON.stringify(data), { headers });
}
function julianDay(d) {
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
function sunMoon(now = /* @__PURE__ */ new Date()) {
  const jd = julianDay(now);
  const n = jd - 2451545;
  const L = (280.46 + 0.9856474 * n) % 360 * (Math.PI / 180);
  const g = (357.528 + 0.9856003 * n) % 360 * (Math.PI / 180);
  const lam = L + (1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * (Math.PI / 180);
  const eps = (23.439 - 4e-7 * n) * (Math.PI / 180);
  const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam));
  const lst = (now.getUTCHours() + now.getUTCMinutes() / 60) % 24;
  const M = (134.963 + 13.064993 * n) % 360 * (Math.PI / 180);
  return {
    timestamp: now.toISOString(),
    lst_hours_utc: Math.round(lst * 100) / 100,
    sun: {
      subsolar_lat: Math.round(dec * 180 / Math.PI * 100) / 100,
      subsolar_lon: Math.round((ra * 180 / Math.PI - lst * 15 + 180) % 360 - 180 * 100) / 100
    },
    moon: { illumination: Math.round((1 - Math.cos(M)) / 2 * 1e3) / 1e3 }
  };
}
async function geoBridge() {
  const feeds = ["schumann_resonance", "nasa_donki_flares", "weather_local"];
  const out = { source: GEO_API, feeds: {} };
  await Promise.all(
    feeds.map(async (id) => {
      try {
        const r = await fetch(`${GEO_API}/v1/stream/${id}`);
        out.feeds[id] = r.ok ? await r.json() : { error: r.status };
      } catch (e) {
        out.feeds[id] = { error: String(e) };
      }
    })
  );
  return out;
}
var MIME = {
  ".html": "text/html;charset=utf-8",
  ".css": "text/css;charset=utf-8",
  ".js": "application/javascript;charset=utf-8",
  ".json": "application/json;charset=utf-8"
};
function mime(path) {
  const ext = path.slice(path.lastIndexOf("."));
  return MIME[ext] || "application/octet-stream";
}
var standalone_default = {
  async fetch(request, _env, ctx) {
    const corsH = cors(request);
    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: corsH });
    const url = new URL(request.url);
    let path = url.pathname;
    if (path === "/embed")
      path = "/";
    if (path === "/api/health") {
      return json({ service: "udm-earth-engine", status: "ok", edge: true, mode: "standalone" }, corsH, 30);
    }
    if (path === "/api/live/ephemeris")
      return json(sunMoon(), corsH, 120);
    if (path === "/api/live/geo") {
      const key = new Request(request.url, { method: "GET" });
      const hit = await caches.default.match(key);
      if (hit) {
        const out2 = new Response(hit.body, hit);
        Object.entries(corsH).forEach(([k, v]) => out2.headers.set(k, v));
        return out2;
      }
      const payload = await geoBridge();
      const res = json(payload, corsH, 60);
      ctx.waitUntil(caches.default.put(key, res.clone()));
      return res;
    }
    const assetPath = path === "/" ? "/index.html" : path;
    const upstream = `${GITHUB_RAW}${assetPath}`;
    const cache = caches.default;
    const cacheKey = new Request(upstream, { method: "GET" });
    let asset = await cache.match(cacheKey);
    if (!asset) {
      asset = await fetch(upstream, { cf: { cacheTtl: 3600 } });
      if (asset.ok)
        ctx.waitUntil(cache.put(cacheKey, asset.clone()));
    }
    const out = new Response(asset.body, asset);
    out.headers.set("Content-Type", mime(assetPath));
    out.headers.set("X-Edge", "udm-earth-engine");
    Object.entries(corsH).forEach(([k, v]) => out.headers.set(k, v));
    if (assetPath.includes("/data/layers/")) {
      out.headers.set("Cache-Control", "public, max-age=86400, immutable");
    } else if (assetPath.endsWith("manifest.json")) {
      out.headers.set("Cache-Control", "public, max-age=300");
    }
    return out;
  }
};
export {
  standalone_default as default
};
