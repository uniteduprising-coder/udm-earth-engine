#!/usr/bin/env python3
"""Bake compact layer bundles for CDN edge delivery (no runtime Python needed)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth.config import get_settings  # noqa: E402
from earth.handlers.forensic_bridge import _import_forensic_parser  # noqa: E402
from earth.handlers.seed_layers import load_seed  # noqa: E402
from earth.handlers.sites_kml import classify_sites, load_enriched_sites  # noqa: E402

OUT = ROOT / "public" / "data"


def compact_site(site: dict) -> dict:
    return {
        "i": site.get("id") or site.get("site_id"),
        "n": site.get("name") or site.get("site_name") or "",
        "la": round(float(site["lat"]), 6),
        "lo": round(float(site["lon"]), 6),
        **({"t": site["structure_type"]} if site.get("structure_type") else {}),
        **({"th": site["thread"]} if site.get("thread") else {}),
        **({"g": site["geometry_type"]} if site.get("geometry_type") else {}),
    }


def bake() -> dict:
    settings = get_settings()
    layers_cfg = settings.load_layers()
    sites = load_enriched_sites(Path(settings.kml_enriched_path))
    classified = classify_sites(sites, layers_cfg)

    manifest_layers = []
    layer_files: dict[str, int] = {}

    for layer in layers_cfg:
        if not layer.get("enabled", True):
            continue
        lid = layer["id"]
        handler = layer.get("handler", "")

        if handler == "sites_kml":
            layer_sites = [compact_site(s) for s in classified.get(lid, [])]
        elif handler == "suppressed_events":
            layer_sites = [compact_site(s) for s in load_seed(settings, "suppressed_events.json")]
        elif handler == "masonic_temples":
            layer_sites = [compact_site(s) for s in load_seed(settings, "masonic_temples.json")]
        elif handler == "forensic_bridge":
            layer_sites = []
            parse_fn = _import_forensic_parser()
            kml_path = Path(settings.forensic_kml_path)
            if parse_fn and kml_path.exists():
                parsed = parse_fn(kml_path)
                for thread, block in parsed.get("layers", {}).items():
                    for site in block.get("sites", []):
                        layer_sites.append(compact_site({**site, "thread": thread}))
        else:
            layer_sites = []

        layer_path = OUT / "layers" / f"{lid}.json"
        layer_path.parent.mkdir(parents=True, exist_ok=True)
        layer_path.write_text(
            json.dumps({"id": lid, "sites": layer_sites}, separators=(",", ":")),
            encoding="utf-8",
        )
        layer_files[lid] = len(layer_sites)
        manifest_layers.append(
            {
                "id": lid,
                "label": layer["label"],
                "icon": layer.get("icon", ""),
                "color": layer.get("color", "#64748b"),
                "count": len(layer_sites),
            }
        )

    built_at = datetime.now(UTC).isoformat()
    manifest = {
        "version": 1,
        "built_at": built_at,
        "projection": "udm_flat_client",
        "constants": {
            "PHI_WIND_DEG": 70.55,
            "PHI_NODE_DEG": -19.45,
            "ALPHA_ANTI_H": 16.9,
            "KAPPA": 0.0514,
        },
        "layers": manifest_layers,
        "totals": layer_files,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = bake()
    print(f"Baked {len(m['layers'])} layers → {OUT}")
    for lid, n in m["totals"].items():
        print(f"  {lid}: {n} sites")