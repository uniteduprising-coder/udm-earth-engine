# UDM Earth Engine

Independent but connectible Earth model for United Uprising — Google Maps / NASA-style layers with **UDM flat projection** (`W(φ)`, Bloch node, stator phase).

## Quick start

```powershell
cd C:\Users\User\united-uprising-ecosystem\udm-earth-engine
py -3 -m pip install -r requirements.txt
$env:PYTHONPATH="src"
py -3 -m earth.main
```

Open http://127.0.0.1:8790

## API

- `GET /v1/layers` — layer dropdown metadata
- `GET /v1/layer/{id}` — GeoJSON with UDM-corrected coordinates
- `POST /v1/refresh` — refresh all feeds + layers
- `GET /v1/projection/project?lat=&lon=&lst_hours=`

## Deploy

- GitHub: `uniteduprising-coder/udm-earth-engine`
- Cloudflare Worker: `earth.uniteduprising.com` → origin on port 8790

## Enki

Use `connectors/earth_connector.py` or open `/embed` inside Enki Terminal Agent dashboard.