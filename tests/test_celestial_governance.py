"""North Axis Aperture and Celestial Governance layer tests."""

from earth.config import ROOT
from earth.cosmology.celestial_governance import (
    evaluate_observer,
    governance_summary,
    north_star_apparent_altitude,
)


def test_governance_files_present():
    assert (ROOT / "docs" / "North_Axis_Aperture_and_Celestial_Governance.md").exists()
    assert (ROOT / "config" / "celestial_governance.yaml").exists()


def test_north_star_altitude_formula():
    assert north_star_apparent_altitude(45.0) == 45.0
    assert north_star_apparent_altitude(30.0, R_f=0.5) == 30.5


def test_evaluate_observer_matches_latitude_rule():
    result = evaluate_observer(60.0)
    assert result["alpha_N_deg"] == 60.0
    assert result["matches_latitude_rule"] is True


def test_governance_summary_structure():
    s = governance_summary()
    assert s["north_axis_aperture"]["alias"] == "North Fixed Star"
    assert len(s["hierarchy"]) >= 8
    assert len(s["classification_table"]) >= 13
    assert "saturn" in s
    assert "jupiter" in s
    assert s["saturn"]["role"] == "step_down_frequency_regulator"
    assert s["jupiter"]["role"] == "charge_flywheel_and_field_distributor"


def test_optical_planets_listed():
    s = governance_summary()
    bodies = s["optical_planets"]["bodies"]
    assert "Mercury" in bodies
    assert "Neptune" in bodies
    assert "Saturn" not in bodies