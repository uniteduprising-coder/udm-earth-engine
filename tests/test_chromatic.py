import math

from earth.cosmology.chromatic import (
    day_night_state,
    full_chromatic_synthesis,
    solar_geometry,
    solar_spectrum_analysis,
)


def test_solar_angular_diameter():
    g = solar_geometry()
    assert g["diameter_mi"] == 33.0
    assert g["altitude_mi"] == 3000.0
    assert 0.5 < g["angular_diameter_deg"] < 0.7


def test_spectrum_dominant_557():
    s = solar_spectrum_analysis()
    assert s["dominant_wavelength_nm"] == 557.0
    assert s["uv_below_391_nm"] is False


def test_day_night_phases():
    near = day_night_state(3600.0, 0.0)
    far = day_night_state(8000.0, math.pi)
    assert near["phase"] in ("day", "twilight")
    assert far["phase"] == "night"


def test_full_synthesis():
    report = full_chromatic_synthesis(lat=45.0, lon=-90.0)
    assert report["version"] == "5.2β"
    assert "skin" in report
    assert report["summary"]["skin_undertone"] == "greenish-golden"
    assert len(report["testable_predictions"]) >= 5