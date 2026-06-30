from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

from earth.handlers.base import FeedHandler
from earth.projection.udm import feature_collection


def _import_forensic_parser():
    geo_src = Path(__file__).resolve().parents[4] / "geo-stream-engine" / "src"
    if geo_src.exists() and str(geo_src) not in sys.path:
        sys.path.insert(0, str(geo_src))
    try:
        from geo.handlers.forensic_kml import parse_forensic_kml  # type: ignore

        return parse_forensic_kml
    except Exception:
        return None


class ForensicBridgeHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        parse_fn = _import_forensic_parser()
        kml_path = Path(feed.get("kml_path") or self.settings.forensic_kml_path)
        if parse_fn and kml_path.exists():
            parsed = parse_fn(kml_path)
            sites = []
            for thread, block in parsed.get("layers", {}).items():
                for site in block.get("sites", []):
                    sites.append({**site, "thread": thread, "layer_id": "forensic_mc04_mc05"})
            geojson = feature_collection(sites, layer_id="forensic_mc04_mc05")
            return self.cache(
                feed["id"],
                {
                    "source": str(kml_path),
                    "threads": list(parsed.get("layers", {}).keys()),
                    "count": len(sites),
                    "geojson": geojson,
                    "raw_geojson": parsed.get("geojson"),
                },
            )

        geo_base = self.settings.geo_stream_local if self.settings.app_env == "development" else self.settings.geo_stream_base
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{geo_base}/v1/stream/forensic_mc05_sediment")
                resp.raise_for_status()
                remote = resp.json()
            payload = remote.get("payload", remote)
            features = payload.get("geojson", {}).get("features", [])
            sites = []
            for f in features:
                if f.get("geometry", {}).get("type") != "Point":
                    continue
                lon, lat = f["geometry"]["coordinates"][:2]
                props = f.get("properties", {})
                sites.append(
                    {
                        "id": f.get("id"),
                        "name": props.get("name", ""),
                        "lat": lat,
                        "lon": lon,
                        **props,
                        "layer_id": "forensic_mc04_mc05",
                    }
                )
            return self.cache(
                feed["id"],
                {
                    "source": f"{geo_base}/v1/stream/forensic_mc05_sediment",
                    "count": len(sites),
                    "geojson": feature_collection(sites, layer_id="forensic_mc04_mc05"),
                },
            )
        except Exception as exc:
            return self.cache(
                feed["id"],
                {"error": str(exc), "hint": "Set FORENSIC_KML_PATH or run geo-stream-engine"},
            )