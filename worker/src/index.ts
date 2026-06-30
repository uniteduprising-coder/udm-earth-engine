import { corsHeaders } from "./cors";

export interface Env {
  UPSTREAM_ORIGIN: string;
}

function applyCors(response: Response, cors: Record<string, string>): Response {
  const out = new Response(response.body, response);
  Object.entries(cors).forEach(([k, v]) => out.headers.set(k, v));
  out.headers.set("X-Edge-Proxy", "udm-earth-engine");
  return out;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const cors = corsHeaders(request);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);
    const upstream = new URL(url.pathname + url.search, env.UPSTREAM_ORIGIN);
    const isCacheable =
      request.method === "GET" &&
      (url.pathname === "/health" ||
        url.pathname.startsWith("/v1/stream/") ||
        url.pathname.startsWith("/v1/layer/"));

    if (isCacheable) {
      const cached = await caches.default.match(new Request(request.url, { method: "GET" }));
      if (cached) return applyCors(cached, cors);
    }

    const res = await fetch(upstream.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    const out = applyCors(res, cors);
    if (isCacheable) {
      out.headers.set("Cache-Control", "public, max-age=30, stale-while-revalidate=120");
      ctx.waitUntil(caches.default.put(new Request(request.url, { method: "GET" }), out.clone()));
    }
    return out;
  },
};