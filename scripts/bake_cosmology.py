#!/usr/bin/env python3
"""Bake cosmology params + nodes for edge CDN."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth.api.advantage_routes import export_advantage_json
from earth.api.cosmology_routes import bake_public_assets
from earth.cosmology.chromatic import full_chromatic_synthesis
from earth.cosmology.engine import get_engine, reset_engine
from earth.cosmology.params import load_node_table
from earth.cosmology.validation import run_validation

OUT = ROOT / "public" / "data" / "cosmology"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bake_public_assets()
    reset_engine()
    engine = get_engine()
    for _ in range(10):
        engine.macro_step_tick()
    state = engine.state()
    validation = run_validation(engine)
    (OUT / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    (OUT / "nodes.json").write_text(json.dumps(load_node_table(), indent=2), encoding="utf-8")
    chromatic = full_chromatic_synthesis(r_mi=70.0, theta_rad=0.785)
    (OUT / "chromatic.json").write_text(json.dumps(chromatic, indent=2), encoding="utf-8")
    export_advantage_json()
    print(f"Baked cosmology assets → {OUT}")


if __name__ == "__main__":
    main()