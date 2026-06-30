"""
GPU AMR scaffold — non-blocking engineering stub (v5.2β).
Full implementation deferred to amr_driver.cu.
"""

from __future__ import annotations

from typing import Any

from earth.cosmology.params import load_params


def amr_config() -> dict[str, Any]:
    P = load_params()
    return {
        "enabled": P.get("amr_enabled", P.get("gpu_amr_enabled", False)),
        "levels": P.get("amr_levels", 3),
        "patch_size": P.get("amr_patch_size", 32),
        "refine_factor": P.get("theta_refine_factor", 8),
        "island_patches": [
            {"r_mi": P["r_iso"], "theta_rad": 0.785 + n * 1.571, "refinement": 8}
            for n in range(4)
        ],
        "status": "scaffold",
        "note": "TODO: wire amr_driver.cu for full GPU island-patch refinement",
        "driver": "amr_driver.cu",
    }


def amr_grid_summary() -> dict[str, Any]:
    P = load_params()
    base_n = P.get("theta_global_N", 512)
    levels = P.get("amr_levels", 3)
    grids = []
    for lv in range(levels + 1):
        factor = 2**lv
        grids.append(
            {
                "level": lv,
                "theta_cells": base_n * factor,
                "r_cells": 550,
                "z_cells": 12,
                "refinement": factor,
            }
        )
    return {
        "base_resolution": f"550×{base_n}×12",
        "levels": grids,
        "oversampling_near_islands": f"{P.get('theta_refine_factor', 8)}×",
    }