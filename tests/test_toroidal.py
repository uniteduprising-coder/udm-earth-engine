"""UDM v5.2β toroidal domain tests."""

import math

from earth.cosmology.below_cell import below_cell_sample, twin_cell_mass_balance
from earth.cosmology.params import load_params
from earth.cosmology.toroidal import (
    domain_extents,
    exterior_void_properties,
    field_sample_3d,
    is_inside_domain,
    toroidal_state,
    view_mode_config,
)
from earth.cosmology.km_optimiser import km_sweep
from earth.cosmology.amr_scaffold import amr_config


def test_params_v52beta():
    p = load_params()
    assert p["r_base"] == 3200
    assert p["R_disk"] == 12500
    assert p["z_max"] == 700
    assert p["z_T"] == 3200
    assert p["C_total"] == 0.115
    assert p["Km"] == 0.0013
    assert p["nu_b"] == 5.9e-5
    assert p["K_m"] == 0.0013  # alias
    assert p["rho_a0"] == 1.2e-6


def test_domain_extents():
    d = domain_extents()
    assert d["vertical_span_mi"] == 3900
    assert d["realms"]["lower"]["name"] == "Below-Cell Abyss"


def test_exterior_void():
    v = exterior_void_properties()
    assert v["opacity"] == 1.0
    assert v["sigma_Sm"] == 0.0


def test_inside_domain():
    assert is_inside_domain(100.0, 0.0)
    assert not is_inside_domain(13000.0, 0.0)
    assert not is_inside_domain(100.0, -4000.0)


def test_below_cell_sample():
    s = below_cell_sample(70.0, math.pi / 4, -500.0, 0.0, load_params())
    assert s["realm"] == "below_cell"
    assert s["V_h"]["theta"] != 0 or s["z_mi"] < 0


def test_twin_cell_steady_state():
    t = twin_cell_mass_balance(load_params())
    assert t["steady_state"] is True
    assert abs(t["net_mass_exchange"]) < 1e-9


def test_field_sample_exterior():
    out = field_sample_3d(13000.0, 0.0, 0.0, 0.0)
    assert out["inside_domain"] is False
    assert out["realm"] == "exterior_void"


def test_view_modes():
    cfg = view_mode_config("underside")
    assert cfg["mode"] == "underside"
    assert "camera" in cfg


def test_toroidal_state():
    st = toroidal_state()
    assert st["version"] == "5.2β"
    assert st["twin_cell"]["steady_state"] is True


def test_km_optimiser():
    r = km_sweep(steps=5)
    assert r["optimal_Km"] > 0
    assert len(r["sweep"]) == 5


def test_amr_scaffold():
    c = amr_config()
    assert c["status"] == "scaffold"
    assert c["levels"] == 3