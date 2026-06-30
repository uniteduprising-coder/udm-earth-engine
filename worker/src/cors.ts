const ALLOWED = new Set([
  "https://uniteduprising.com",
  "https://www.uniteduprising.com",
  "https://earth.uniteduprising.com",
  "http://localhost:5173",
  "http://localhost:8790",
  "http://127.0.0.1:8790",
]);

export function corsHeaders(request: Request): Record<string, string> {
  const origin = request.headers.get("Origin") ?? "";
  const allow = ALLOWED.has(origin) ? origin : "https://uniteduprising.com";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Signature",
    "Access-Control-Max-Age": "86400",
  };
}