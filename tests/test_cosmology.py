import math

from earth.cosmology.coordinates import cylindrical_to_geo, geo_to_cylindrical, project_site
from earth.cosmology.engine import CosmologyEngine
from earth.cosmology.fields import B_stat, V_r_a, V_r_h, glow_intensity
from earth.cosmology.params import load_params
from earth.cosmology.validation import run_validation


def test_params_loaded():
    p = load_params()
    assert p["L_f"] == 2.428
    assert p["r_base"] == 12.752
    assert p["R_disk"] == 12500
    assert p["T_a_period_min"] == 14.2


def test_geo_cylindrical_roundtrip_pole():
    cyl = geo_to_cylindrical(90.0, 0.0)
    assert cyl["r_mi"] == 0.0
    geo = cylindrical_to_geo(0.0, 0.0)
    assert abs(geo["lat"] - 90.0) < 0.01


def test_geo_cylindrical_equator():
    cyl = geo_to_cylindrical(0.0, 45.0, R_disk=12500.0)
    assert abs(cyl["r_mi"] - 12500.0) < 1.0


def test_drain_velocities_at_1mi():
    p = load_params()
    # Base drain at θ where river modulation cos(4θ)=0 (intercardinal)
    vr_h = V_r_h(1.0, math.pi / 8, p)
    vr_a = V_r_a(1.0, p)
    assert abs(vr_h + 0.138) < 0.02
    assert abs(vr_a + 0.0165) < 0.005


def test_aether_period_14_2min():
    p = load_params()
    period_min = (2 * math.pi / p["omega_a"]) / 60
    assert abs(period_min - 14.2) < 0.3


def test_engine_state():
    engine = CosmologyEngine()
    state = engine.state()
    assert state["version"] == "5.1"
    assert state["Omega0"] == p["Omega0_init"] if (p := load_params()) else True
    assert len(state["nodes"]) == 6


def test_validation_suite():
    engine = CosmologyEngine()
    report = run_validation(engine)
    assert report["total_checks"] == 17
    assert report["passed"] >= 10


def test_project_site_v5():
    proj = project_site(45.0, -90.0, mode="udm_v5")
    assert "r_mi" in proj
    assert "theta_rad" in proj
    assert "r_french_mi" in proj