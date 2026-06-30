# UDM Earth Engine

**Edge-first** Earth map — pre-baked site layers on Cloudflare CDN, UDM projection in the browser (zero lag on layer/time changes).

## How it works (fast path)

| What | Where | Latency |
|------|--------|---------|
| Map UI + site dots | `public/` → Cloudflare edge | ~50ms first paint |
| Layer data | `/data/layers/*.json` (baked, immutable cache) | One small fetch per layer |
| UDM warp / time slider | Browser only | **0ms** — no server round-trip |
| Sun / moon / geo feeds | `/api/live/*` at edge | Background, non-blocking |

No Python server required for users. Python is **bake + optional ingest** only.

## Production

**https://earth.uniteduprising.com**

## Develop locally

```powershell
cd udm-earth-engine
py -3 -m pip install -r requirements.txt
$env:PYTHONPATH="src"
py -3 scripts/bake_atlas.py    # refresh public/data
npm install
npm run dev                   # wrangler dev → http://localhost:8787
```

## Update site data

```powershell
py -3 scripts/bake_atlas.py
git add public/data
git push   # CI redeploys to Cloudflare
```

## Enki / Mission Control

- Enki opens `https://earth.uniteduprising.com` by default
- Terminal Agent toolbar **🌍 Earth**
- Mission Control embeds the same URL

## Optional Python API (port 8790)

Legacy ingest server for heavy refresh jobs — not on the user hot path:

```powershell
$env:PYTHONPATH="src"; py -3 -m earth.main
```