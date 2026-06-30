import { corsHeaders } from "./cors";
import { handleCosmologyApi } from "./cosmology_routes";
import { geoBridge, sunMoonEphemeris } from "./live";

export interface Env {
  GEO_API?: string;
  ASSETS: Fetcher;
}

function withCors(res: Response, cors: Record<string, string>): Response {
  const out = new Response(res.body, res);
  Object.entries(cors).forEach(([k, v]) => out.headers.set(k, v));
  out.headers.set("X-Edge", "udm-earth-engine");
  return out;
}

function json(data: unknown, cors: Record<string, string>, cacheSec = 0): Response {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...cors };
  if (cacheSec > 0) headers["Cache-Control"] = `public, max-age=${cacheSec}, stale-while-revalidate=${cacheSec * 2}`;
  return new Response(JSON.stringify(data), { headers });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const cors = corsHeaders(request);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return json(
        {
          service: "udm-earth-engine",
          status: "ok",
          edge: true,
          mode: "static-atlas",
          cosmology_engine: "5.2β",
          projection: "udm_v5",
        },
        cors,
        30
      );
    }

    if (url.pathname === "/api/live/ephemeris") {
      return json(sunMoonEphemeris(), cors, 120);
    }

    if (url.pathname === "/api/live/geo") {
      const cache = caches.default;
      const key = new Request(request.url, { method: "GET" });
      const hit = await cache.match(key);
      if (hit) return withCors(hit, cors);
      const payload = await geoBridge(env);
      const res = json(payload, cors, 60);
      ctx.waitUntil(cache.put(key, res.clone()));
      return res;
    }

    const cosmology = await handleCosmologyApi(request, env, cors);
    if (cosmology) return cosmology;

    if (url.pathname.startsWith("/data/")) {
      const asset = await env.ASSETS.fetch(request);
      if (asset.status === 404) return withCors(asset, cors);
      const out = new Response(asset.body, asset);
      if (url.pathname.endsWith("manifest.json")) {
        out.headers.set("Cache-Control", "public, max-age=300, stale-while-revalidate=600");
      } else if (url.pathname.includes("/layers/")) {
        out.headers.set("Cache-Control", "public, max-age=86400, immutable");
      }
      return withCors(out, cors);
    }

    const asset = await env.ASSETS.fetch(request);
    return withCors(asset, cors);
  },
};