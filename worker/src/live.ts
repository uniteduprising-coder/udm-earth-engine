/** Lightweight live feeds — computed at edge, no Python origin. */

export function sunMoonEphemeris(now = new Date()): Record<string, unknown> {
  const jd = julianDay(now);
  const n = jd - 2451545.0;
  const L = deg2rad((280.46 + 0.9856474 * n) % 360);
  const g = deg2rad((357.528 + 0.9856003 * n) % 360);
  const lam = L + deg2rad(1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g));
  const eps = deg2rad(23.439 - 0.0000004 * n);
  const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam));
  const lstHours = (now.getUTCHours() + now.getUTCMinutes() / 60) % 24;
  const subsolarLon = (rad2deg(ra) - lstHours * 15 + 180) % 360 - 180;

  const mLam = deg2rad((218.316 + 13.176396 * n) % 360);
  const M = deg2rad((134.963 + 13.064993 * n) % 360);
  const F = deg2rad((93.272 + 13.22935 * n) % 360);
  const moonLon = mLam + deg2rad(6.289 * Math.sin(M));
  const moonLat = deg2rad(5.128 * Math.sin(F));
  const illumination = (1 - Math.cos(M)) / 2;

  return {
    timestamp: now.toISOString(),
    lst_hours_utc: round(lstHours, 2),
    sun: {
      subsolar_lat: round(rad2deg(dec), 2),
      subsolar_lon: round(subsolarLon, 2),
    },
    moon: {
      illumination: round(illumination, 3),
      ecliptic_lat_deg: round(rad2deg(moonLat), 2),
      ecliptic_lon_deg: round(rad2deg(moonLon) % 360, 2),
    },
  };
}

export async function geoBridge(env: { GEO_API?: string }): Promise<Record<string, unknown>> {
  const base = env.GEO_API || "https://geo-api.uniteduprising.com";
  const feeds = ["schumann_resonance", "nasa_donki_flares", "weather_local"];
  const out: Record<string, unknown> = { source: base, feeds: {} as Record<string, unknown> };
  await Promise.all(
    feeds.map(async (id) => {
      try {
        const r = await fetch(`${base}/v1/stream/${id}`, { cf: { cacheTtl: 60 } });
        (out.feeds as Record<string, unknown>)[id] = r.ok ? await r.json() : { error: r.status };
      } catch (e) {
        (out.feeds as Record<string, unknown>)[id] = { error: String(e) };
      }
    })
  );
  return out;
}

function julianDay(d: Date): number {
  let y = d.getUTCFullYear();
  let m = d.getUTCMonth() + 1;
  const day =
    d.getUTCDate() +
    (d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600) / 24;
  if (m <= 2) {
    y -= 1;
    m += 12;
  }
  const a = Math.floor(y / 100);
  const b = 2 - a + Math.floor(a / 4);
  return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + day + b - 1524.5;
}

function deg2rad(d: number) {
  return (d * Math.PI) / 180;
}
function rad2deg(r: number) {
  return (r * 180) / Math.PI;
}
function round(v: number, p: number) {
  const f = 10 ** p;
  return Math.round(v * f) / f;
}