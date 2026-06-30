# UDM Earth Engine — Edge Architecture

## User hot path (zero bottleneck)

```
Browser
  ├─ GET /                    → static HTML (edge)
  ├─ GET /data/manifest.json  → layer menu (5 min cache)
  ├─ GET /data/layers/{id}.json → compact sites (24h immutable)
  ├─ UDM projection           → 100% client-side
  └─ GET /api/live/*          → async after map visible
```

## Why this is fast

1. **No per-click API** — layer switch uses in-memory cache
2. **No Python on request path** — bake runs in CI or manually
3. **Canvas map** — `preferCanvas: true` for hundreds of markers
4. **Prefetch** — idle-time loads remaining layers
5. **LST slider** — debounced client re-project only

## Repo layout

| Path | Role |
|------|------|
| `public/` | Cloudflare static assets (UI + baked data) |
| `scripts/bake_atlas.py` | KML → compact JSON |
| `worker/` | Edge API (live feeds only) |
| `src/earth/` | Optional Python ingest (off hot path) |

## Deploy

`git push` → GitHub Actions → `bake_atlas.py` → `wrangler deploy` → `earth.uniteduprising.com`