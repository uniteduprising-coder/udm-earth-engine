import math

from earth.cosmology.coordinates import cylindrical_to_geo, geo_to_cylindrical, project_site
from earth.cosmology.engine import CosmologyEngine
from earth.cosmology.fields import B0_field, V_r_a, V_r_h, glow_azimuthal_ratio, schumann_q_factor
from earth.cosmology.params import load_params, load_luminary_spectra
from earth.cosmology.validation import run_validation


def test_params_v52beta():
    p = load_params()
    assert p["r_base"] == 3200
    assert p["C_iso"] == 0.071
    assert p["C_total"] == 0.115
    assert p["Omega_max"] == 4.9
    assert p["Z_g"] == 2.8
    assert p["d_iso"] == 14.0
    assert p["K_m"] == 0.0013
    assert p["I_rot"] == 2.3e24


def test_B0_ledger():
    p = load_params()
    assert abs(B0_field(p) - 8.2e-6) < 1e-7


def test_geo_cylindrical_roundtrip_pole():
    cyl = geo_to_cylindrical(90.0, 0.0)
    assert cyl["r_mi"] == 0.0
    geo = cylindrical_to_geo(0.0, 0.0)
    assert abs(geo["lat"] - 90.0) < 0.01


def test_drain_velocities_at_1mi():
    p = load_params()
    vr_h = V_r_h(1.0, math.pi / 8, p)
    vr_a = V_r_a(1.0, p)
    assert abs(vr_h + 0.138) < 0.02
    assert abs(vr_a + 0.0165) < 0.005


def test_schumann_q():
    p = load_params()
    q = schumann_q_factor(p)
    assert 8 <= q <= 12


def test_engine_state_v52():
    engine = CosmologyEngine()
    state = engine.state()
    assert state["version"] == "5.2β"
    assert state["C_total_F"] == 0.115
    assert state["Z_g_ohm"] == 2.8
    assert len(state["nodes"]) == 6
    sun = next(n for n in state["nodes"] if n["type"] == "Sun")
    assert sun["z_mi"] == 3000.0


def test_validation_18_checks():
    engine = CosmologyEngine()
    report = run_validation(engine)
    assert report["total_checks"] == 18
    assert report["blocking_gaps"] == 0
    assert report["passed"] >= 14


def test_glow_azimuthal_ratio():
    p = load_params()
    ratio = glow_azimuthal_ratio(70.0, 0.0, p)
    assert 0.94 <= ratio <= 1.06


def test_luminary_spectra():
    lines = load_luminary_spectra()
    assert len(lines) == 5
    assert lines[2]["wavelength_nm"] == "557"


def test_project_site_v5():
    proj = project_site(45.0, -90.0, mode="udm_v5")
    assert "r_mi" in proj
    assert "r_french_mi" in proj