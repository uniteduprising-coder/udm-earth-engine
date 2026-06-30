"""UDM Real-Time Earth Model tests."""

import math

from earth.config import ROOT
from earth.realtime.coordinates import (
    phi_udm_from_rho,
    plate_to_rho_theta,
    rho_from_phi_udm,
)
from earth.realtime.paths import MODEL_ROOT


def test_model_structure_exists():
    assert (MODEL_ROOT / "config" / "udm_master_plate.yaml").exists()
    assert (MODEL_ROOT / "config" / "sources.yaml").exists()
    assert (MODEL_ROOT / "plates" / "README.md").exists()


def test_udm_coordinate_system():
    cx, cy, r_outer = 767.0, 766.0, 766.0
    rho, theta = plate_to_rho_theta(cx, cy, cx, cy, r_outer)
    assert rho == 0.0
    assert phi_udm_from_rho(0.0) == 90.0
    assert math.isclose(rho_from_phi_udm(0.0), 0.5)
    assert math.isclose(rho_from_phi_udm(-90.0), 1.0)


def test_disk_solver_runs():
    import yaml
    from earth.realtime.disk_solver import solve_disk

    with (MODEL_ROOT / "config" / "udm_master_plate.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    disk = solve_disk(cfg)
    assert disk["plate_lock"] is True
    assert disk["center_px_initial"] == [767, 766]


def test_control_points_minimum():
    import yaml
    from earth.realtime.control_points import build_control_points

    with (MODEL_ROOT / "config" / "udm_master_plate.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cp = build_control_points(cfg)
    assert cp["count"] >= 12
    assert cp["grade"] == "crude"