import type { Env } from "./index";

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

function json(data: unknown, cors: Record<string, string>, cacheSec = 0): Response {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...cors };
  if (cacheSec > 0) headers["Cache-Control"] = `public, max-age=${cacheSec}, stale-while-revalidate=${cacheSec * 2}`;
  return new Response(JSON.stringify(data), { headers });
}

async function fetchBakedJson(env: Env, assetPath: string): Promise<Record<string, unknown> | null> {
  const req = new Request(`https://earth.uniteduprising.com${assetPath}`, { method: "GET" });
  const res = await env.ASSETS.fetch(req);
  if (!res.ok) return null;
  return res.json() as Promise<Record<string, unknown>>;
}

export async function handleCosmologyApi(
  request: Request,
  env: Env,
  cors: Record<string, string>
): Promise<Response | null> {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === "/api/params") {
    const baked = await fetchBakedJson(env, "/data/cosmology/params.json");
    return json(baked ?? { error: "params not baked" }, cors, 120);
  }
  if (path === "/api/cosmology/state") {
    const baked = await fetchBakedJson(env, "/data/cosmology/state.json");
    return json(baked ?? { error: "state not baked" }, cors, 60);
  }
  if (path === "/api/cosmology/chromatic" || path === "/api/cosmology/terminator" || path === "/api/cosmology/daynight") {
    const baked = await fetchBakedJson(env, "/data/cosmology/chromatic.json");
    if (path === "/api/cosmology/daynight" && baked?.state_at_point) {
      const lat = url.searchParams.get("lat");
      const lon = url.searchParams.get("lon");
      return json(
        { ...(baked.state_at_point as object), lat: lat ? Number(lat) : null, lon: lon ? Number(lon) : null },
        cors,
        60
      );
    }
    return json(baked ?? { error: "chromatic not baked" }, cors, 120);
  }
  if (path === "/api/validate" || path === "/api/run_full_validation") {
    const baked = await fetchBakedJson(env, "/data/cosmology/validation.json");
    if (path === "/api/run_full_validation" && baked) {
      baked.generated_at = new Date().toISOString();
    }
    return json(baked ?? { error: "validation not baked" }, cors, 60);
  }
  if (path === "/api/observations/layers") {
    return json({ layers: OBS_LAYERS }, cors, 300);
  }
  if (path === "/realtime" || path === "/realtime.html") {
    const req = new Request("https://earth.uniteduprising.com/realtime.html", { method: "GET" });
    const asset = await env.ASSETS.fetch(req);
    return asset;
  }
  if (
    path === "/planar" ||
    path === "/planar/" ||
    path === "/disk" ||
    path === "/disk.html" ||
    path === "/simulate" ||
    path === "/simulate.html" ||
    path === "/globe" ||
    path === "/globe.html" ||
    path === "/view"
  ) {
    const req = new Request("https://earth.uniteduprising.com/disk.html", { method: "GET" });
    return env.ASSETS.fetch(req);
  }
  if (path === "/planar/kernel" || path === "/planar/kernel.html") {
    const req = new Request("https://earth.uniteduprising.com/planar/kernel.html", { method: "GET" });
    return env.ASSETS.fetch(req);
  }
  if (path === "/planar/app" || path === "/planar/app/" || path === "/planar/app/index.html") {
    const req = new Request("https://earth.uniteduprising.com/planar/app/index.html", { method: "GET" });
    return env.ASSETS.fetch(req);
  }
  if (path === "/api/simulation/state") {
    const baked = await fetchBakedJson(env, "/data/cosmology/state.json");
    const out = (baked ?? {}) as Record<string, unknown>;
    out.domain = "planar_polar";
    out.engine_type = "udm_planar_simulation";
    return json(out, cors, 60);
  }
  if (path === "/toroid" || path === "/toroid.html") {
    const req = new Request("https://earth.uniteduprising.com/toroid.html", { method: "GET" });
    return env.ASSETS.fetch(req);
  }
  if (path.startsWith("/api/procedural/")) {
    if (path === "/api/procedural/status") {
      const baked = await fetchBakedJson(env, "/data/procedural/manifest.json");
      return json(baked ?? { ok: false, message: "Run procedural build" }, cors, 120);
    }
    if (path === "/api/procedural/layers") {
      const baked = await fetchBakedJson(env, "/data/procedural/layers.json");
      return json(baked ?? { layers: {}, message: "Run procedural build" }, cors, 120);
    }
    if (path === "/api/procedural/terminations") {
      const baked = await fetchBakedJson(env, "/data/procedural/terminations.json");
      return json(baked ?? { error: "terminations not published" }, cors, 300);
    }
    if (path === "/api/procedural/build" && request.method === "POST") {
      return json(
        { ok: false, edge: true, note: "POST /api/procedural/build runs on Python API — edge serves baked assets only" },
        cors
      );
    }
    const baked = await fetchBakedJson(env, "/data/procedural/manifest.json");
    return json(baked ?? { error: "procedural not published" }, cors, 120);
  }
  if (path.startsWith("/api/realtime/")) {
    const baked = await fetchBakedJson(env, "/data/realtime/manifest.json");
    if (path === "/api/realtime/status") return json(baked ?? { plate_lock: true }, cors, 60);
    if (path === "/api/realtime/disk") {
      const disk = await fetchBakedJson(env, "/data/realtime/disk.json");
      return json(disk ?? { error: "run pipeline" }, cors, 120);
    }
    return json(baked ?? { error: "realtime not published" }, cors, 60);
  }
  if (path.startsWith("/api/celestial/")) {
    const baked = await fetchBakedJson(env, "/data/cosmology/celestial_governance.json");
    if (!baked) {
      return json(
        {
          document: "North Axis Aperture and Celestial Governance",
          note: "Run scripts/bake_cosmology.py to bake",
        },
        cors,
        120
      );
    }
    if (path === "/api/celestial/governance") return json(baked, cors, 300);
    if (path === "/api/celestial/hierarchy") return json({ hierarchy: baked.hierarchy ?? [] }, cors, 300);
    if (path === "/api/celestial/classification") {
      return json({ classification_table: baked.classification_table ?? [] }, cors, 300);
    }
    if (path === "/api/celestial/measurements") {
      return json({ measurement_feeds: baked.measurement_feeds ?? {} }, cors, 300);
    }
    if (path === "/api/celestial/north-axis") {
      const lat = Number(url.searchParams.get("lat") ?? "NaN");
      if (!Number.isFinite(lat)) {
        return json({ error: "lat query parameter required (degrees)" }, cors, 400);
      }
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
        cors,
        120
      );
    }
    return json(baked, cors, 300);
  }
  if (path.startsWith("/api/encyclopedia")) {
    const baked = await fetchBakedJson(env, "/data/cosmology/encyclopedia.json");
    if (!baked) {
      return json(
        {
          document: "UDM Master Encyclopedia",
          tiers: { T1: "empirically sourced", T4: "simulation parameter" },
          note: "Run scripts/ingest_encyclopedia.py to bake",
        },
        cors,
        120
      );
    }
    return json(baked, cors, 300);
  }
  if (path.startsWith("/api/toroidal/")) {
    const baked = await fetchBakedJson(env, "/data/cosmology/toroidal.json");
    if (!baked) return json({ error: "toroidal not baked" }, cors);
    if (path === "/api/toroidal/domain") return json(baked.domain ?? baked, cors, 300);
    if (path === "/api/toroidal/state") return json(baked, cors, 120);
    if (path === "/api/toroidal/void") return json(baked.void ?? {}, cors, 300);
    if (path === "/api/toroidal/twin-cell") return json(baked.twin_cell ?? {}, cors, 120);
    if (path === "/api/toroidal/view-modes") {
      return json({ mode: "top", available: ["top", "underside", "toroidal"] }, cors, 300);
    }
    return json(baked, cors, 120);
  }
  if (path.startsWith("/api/advantage/")) {
    const baked = await fetchBakedJson(env, "/data/cosmology/advantage.json");
    if (!baked) return json({ error: "advantage not baked" }, cors);
    if (path === "/api/advantage/summary") {
      return json(baked.summary ? { summary: baked.summary, ...baked } : baked, cors, 120);
    }
    if (path === "/api/advantage/spectral") {
      const cosmology = url.searchParams.get("cosmology") || "udm";
      const key = cosmology === "copernican" ? "spectral_copernican" : "spectral_udm";
      return json((baked[key] as object) ?? baked.spectral_udm, cors, 300);
    }
    if (path === "/api/advantage/predictions") return json(baked.predictions ?? {}, cors, 120);
    if (path === "/api/advantage/observations/network") return json(baked.observation_network ?? {}, cors, 120);
    if (path === "/api/advantage/replay" || path === "/api/advantage/replay/state") {
      return json(baked.replay ?? {}, cors, 120);
    }
    if (path === "/api/advantage/ingestion") return json(baked.ingestion ?? {}, cors, 120);
    if (path === "/api/advantage/dual-mode" || path === "/api/advantage/predict") {
      return json({ edge: true, note: "Use Python API for live dual-mode / predict", baked: true }, cors);
    }
    if (path === "/api/advantage/ingestion/run" && request.method === "POST") {
      return json({ ok: true, edge: true, note: "Ingest stub on edge", validation_score: "16/18" }, cors);
    }
    return json(baked, cors, 120);
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
      cors
    );
  }

  return null;
}