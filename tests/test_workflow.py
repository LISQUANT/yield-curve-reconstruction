import json
from hashlib import sha256
from pathlib import Path
import socket

import pandas as pd
import pytest

from test_bundesbank import snapshot
from test_fed import synthetic_csv
from yieldcurves.sources.fed import save_snapshot
from yieldcurves.workflow import acquire, run


def test_offline_workflow_preserves_inputs_and_matches_dates(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    save_snapshot(synthetic_csv(), data / "us", acquisition="synthetic test fixture")
    snapshot(data / "de")
    (data / "snapshots.json").write_text(json.dumps({"US": "us", "DE": "de"}))
    before = {p: sha256(p.read_bytes()).hexdigest() for p in data.rglob("*") if p.is_file()}
    def no_network(*args, **kwargs):
        raise AssertionError("Offline mode opened a socket")
    monkeypatch.setattr(socket, "socket", no_network)
    output = tmp_path / "result"
    result = run(data, output, "2026-10-18", offline=True)
    assert result["validation_passed"]
    assert result["observation_date"] == "2026-10-02"
    curves = pd.read_csv(output / "curves.csv")
    assert len(curves) == 602 and curves.observation_date.nunique() == 1
    assert (output / "research_note.pdf").read_bytes().startswith(b"%PDF")
    assert before == {p: sha256(p.read_bytes()).hexdigest() for p in before}
    for name, digest in result["output_sha256"].items():
        assert sha256((output / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        run(data, output, "2026-10-18", offline=True)


def test_no_snapshot_offline_fails_without_creating_data(tmp_path):
    with pytest.raises(ValueError, match="No Fed snapshot"):
        acquire(tmp_path / "data", "2026-10-18", offline=True)
    assert not (tmp_path / "data").exists()


def test_official_reference_regression_retains_german_exception():
    from yieldcurves.sources import fed, bundesbank
    record = json.loads((Path(__file__).parent / "fixtures" / "official_reference.json").read_text())
    us = pd.Series(record["US"]["tokens"])
    us["Date"] = pd.Timestamp(record["date"])
    result = fed.validate_reconstruction(us)
    assert result.within_tolerance.all()
    assert result.error_bp.abs().max() == pytest.approx(0.004643039657609149, abs=1e-10)
    de = pd.Series(record["DE"]["tokens"], name=pd.Timestamp(record["date"]))
    result = bundesbank.validate_reconstruction(de)
    assert result.within_tolerance.sum() == 29
    assert not result.within_tolerance.iloc[0]
    assert result.error_bp.iloc[0] == pytest.approx(-0.5279805370423871, abs=1e-9)
