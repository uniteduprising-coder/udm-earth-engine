"""Competitive Advantage Blueprint — module and API tests."""

import math

from earth.cosmology.dual_mode import compare_cosmologies, difference_map, reality_mode_summary
from earth.cosmology.ingestion import ingestion_status, run_ingestion_cycle
from earth.cosmology.predictions import generate_prediction, list_predictions, submit_prediction
from earth.cosmology.replay import replay_metadata, replay_state
from earth.cosmology.spectral import N_BINS, render_spectral, udm_illuminant_spectrum
from earth.cosmology.telemetry import pack_physics_frame, pack_validation_frame


def test_spectral_bins():
    spec = udm_illuminant_spectrum()
    assert len(spec) == N_BINS
    assert spec[0]["wavelength_nm"] == 380.0


def test_spectral_render_udm():
    out = render_spectral(cosmology="udm", melanin=12.0)
    assert out["cosmology"] == "udm"
    assert out["dominant_wavelength_nm"] == 557.0
    assert out["skin"]["hex"].startswith("#")
    assert len(out["skin"]["rgb"]) == 3


def test_dual_mode_compare():
    # r ≈ 70 mi anchor (station #4)
    result = compare_cosmologies(89.496, 45.0)
    assert "udm" in result
    assert "copernican" in result
    assert "divergence" in result
    assert result["udm"]["fields"]["I_glow_cd"] > 0


def test_difference_map():
    grid = difference_map(75.0, 0.0, grid=5)
    assert grid["grid"] == 5
    assert len(grid["cells"]) == 25


def test_reality_mode_summary():
    summary = reality_mode_summary()
    assert summary["cosmology_version"] == "5.2β"
    assert summary["score_pct"] > 0
    assert "validation" in summary


def test_generate_prediction_glow():
    pred = generate_prediction(r_mi=70.0, theta_rad=math.pi / 4, observable="glow")
    assert pred["predictions"]["glow_intensity_cd"] > 0
    assert pred["predictions"]["period_min"] == 14.2


def test_prediction_market():
    market = list_predictions()
    assert market["active_count"] >= 1
    sub = submit_prediction(
        observable="glow",
        r_mi=70.0,
        theta_rad=0.785,
        predicted_value="14.2 min",
        stake_points=50,
    )
    assert sub["ok"] is True


def test_replay_soviet_1982():
    meta = replay_metadata("soviet_1982")
    assert meta["station"] == "#4"
    state = replay_state("soviet_1982", t_offset_s=0.0)
    assert state["comparison"]["match_pct"] > 90


def test_ingestion_cycle():
    status = ingestion_status()
    assert len(status["sources"]) >= 5
    result = run_ingestion_cycle(sources=["schumann", "iers"])
    assert result["ok"] is True
    assert result["validation_score"]


def test_telemetry_frames():
    state = {"Omega0": 2.47, "P_GW": 3.82, "t_sim_s": 0.0, "macro_step": 1, "fields_at_anchor": {"I_cd": 920}}
    frame = pack_physics_frame(1.0, state)
    assert len(frame) == 52  # 16-byte header + 36-byte body
    vframe = pack_validation_frame(1.0, {"passed": 16, "total_checks": 18})
    assert len(vframe) == 32  # 16-byte header + 16-byte body