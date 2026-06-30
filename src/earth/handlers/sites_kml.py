from __future__ import annotations

import json
import re
from pathlib import Path

from earth.config import Settings
from earth.handlers.base import FeedHandler
from earth.projection.udm import feature_collection


def _matches_filter(site: dict, filt: dict) -> bool:
    if not filt:
        return True
    name = (site.get("site_name") or site.get("name") or "").lower()
    st = site.get("structure_type", "")
    geom = site.get("geometry_type", "")
    layer_label = site.get("kml_layer_label", "")

    if types := filt.get("structure_types"):
        if st not in types:
            if not any(t in name for t in types):
                return False
    if geoms := filt.get("geometry_types"):
        if geom not in geoms:
            return False
    if labels := filt.get("kml_layer_labels"):
        if layer_label not in labels:
            return False
    if needles := filt.get("name_contains"):
        if not any(n.lower() in name for n in needles):
            if st not in (filt.get("structure_types") or []):
                return False
    return True


def classify_sites(sites: list[dict], layers: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {layer["id"]: [] for layer in layers}
    for site in sites:
        normalized = {
            "id": site.get("site_id") or site.get("id"),
            "name": site.get("site_name") or site.get("name"),
            "lat": site.get("lat"),
            "lon": site.get("lon"),
            **site,
        }
        for layer in layers:
            if layer.get("handler") != "sites_kml":
                continue
            filt = layer.get("filter") or {}
            if _matches_filter(normalized, filt):
                rec = {**normalized, "layer_id": layer["id"]}
                out[layer["id"]].append(rec)
    return out


def load_enriched_sites(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sites", data if isinstance(data, list) else [])


class SitesLayersHandler(FeedHandler):
    async def fetch(self, feed: dict) -> dict:
        settings: Settings = self.settings
        layers = settings.load_layers()
        sites = load_enriched_sites(Path(settings.kml_enriched_path))
        classified = classify_sites(sites, layers)

        layer_geojson: dict[str, dict] = {}
        counts: dict[str, int] = {}
        for layer in layers:
            lid = layer["id"]
            if layer.get("handler") != "sites_kml":
                continue
            layer_sites = classified.get(lid, [])
            layer_geojson[lid] = feature_collection(layer_sites, layer_id=lid)
            counts[lid] = len(layer_sites)

        return self.cache(
            feed["id"],
            {
                "source": str(settings.kml_enriched_path),
                "total_sites": len(sites),
                "layer_counts": counts,
                "layers": layer_geojson,
            },
        )


def get_layer_payload(settings: Settings, layer_id: str, lst_hours: float = 12.0) -> dict | None:
    cache = settings.cache_path / "sites_layers.json"
    if cache.exists():
        record = json.loads(cache.read_text(encoding="utf-8"))
        layers = record.get("payload", {}).get("layers", {})
        if layer_id in layers:
            return layers[layer_id]

    layers_cfg = settings.load_layers()
    layer = next((l for l in layers_cfg if l["id"] == layer_id), None)
    if not layer or layer.get("handler") != "sites_kml":
        return None
    sites = load_enriched_sites(Path(settings.kml_enriched_path))
    classified = classify_sites(sites, layers_cfg)
    return feature_collection(classified.get(layer_id, []), lst_hours=lst_hours, layer_id=layer_id)