# UDM Earth Engine — Architecture Map

| Path | Layer | Description |
|------|-------|-------------|
| `src/earth/main.py` | entry | FastAPI + scheduler + static UI |
| `src/earth/projection/udm.py` | core | W(φ) flat projection math |
| `src/earth/api/routes.py` | api | layers, feeds, refresh, projection |
| `src/earth/handlers/` | adapter | NASA EPIC, ephemeris, KML layers, geo bridge |
| `config/layers.json` | data | Layer dropdown registry |
| `config/feeds.json` | data | Poll feed registry |
| `frontend/` | ui | Leaflet map + Three.js globe |
| `worker/` | edge | CF Worker → `earth.uniteduprising.com` |

## Ports & Subdomain

| Env | URL |
|-----|-----|
| Local | `http://127.0.0.1:8790` |
| Production | `https://earth.uniteduprising.com` |

## Data Flow

```
Startup / POST /v1/refresh → handlers.fetch() → data/cache/*.json
UI → GET /v1/layer/{id} → GeoJSON with UDM-corrected coordinates
Enki connector → same API + /embed iframe
```

## Enki Integration

- `connectors/earth_connector.py` in Enki desktop repo
- Launch: Enki desktop UDM tab · Terminal Agent toolbar · Mission Control tile