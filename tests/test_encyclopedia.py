"""UDM Master Encyclopedia ingestion tests."""

from pathlib import Path

from earth.config import ROOT
from earth.cosmology.encyclopedia import ingest_encyclopedia, load_jerk_catalogue, provenance_summary


def test_encyclopedia_files_present():
    assert (ROOT / "docs" / "UDM_Master_Encyclopedia.md").exists()
    assert (ROOT / "config" / "udm_engine_params.yaml").exists()


def test_provenance_summary():
    s = provenance_summary()
    assert "T1" in s["tiers"]
    assert s["sourced"]["sidereal"]["miller_k"] == 0.0514


def test_jerk_catalogue_loaded():
    jerks = load_jerk_catalogue()
    assert len(jerks) >= 14
    years = {int(j["year"]) for j in jerks}
    assert 1969 in years
    assert 2014 in years


def test_ingest_encyclopedia_runs():
    result = ingest_encyclopedia()
    assert result["ok"] is True
    assert result["files"]["encyclopedia_md"] is True
    assert "imf_status" in result
    assert Path(ROOT / "validation" / "jerk_report.md").exists()