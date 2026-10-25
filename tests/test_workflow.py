"""Offline integration uses only synthetic data and no manifests."""

import socket
import sys

import pandas as pd
import pytest

from test_bundesbank import snapshot
from test_fed import synthetic_csv
from yieldcurves.sources.fed import save_snapshot
from yieldcurves.workflow import acquire, run


def test_offline_workflow_preserves_inputs_and_matches_dates(tmp_path, monkeypatch):
    data = tmp_path / "data"
    save_snapshot(synthetic_csv(), data / "US")
    snapshot(data / "DE")
    before = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
    def no_network(*args, **kwargs):
        raise AssertionError("Offline mode opened a socket")
    monkeypatch.setattr(socket, "socket", no_network)
    for module in ["reportlab", "svglib", "yieldcurves.report"]:
        monkeypatch.setitem(sys.modules, module, None)
    output = tmp_path / "result"
    result = run(data, output, "2026-10-18", offline=True)
    assert result["validation_passed"]
    assert result["observation_date"] == "2026-10-02"
    curves = pd.read_csv(output / "curves.csv")
    assert len(curves) == 602 and curves.observation_date.nunique() == 1
    assert not (output / "research_note.pdf").exists()
    assert before == {p: p.read_bytes() for p in before}
    assert not (output / "manifest.json").exists()
    with pytest.raises(FileExistsError):
        run(data, output, "2026-10-18", offline=True)


def test_missing_offline_input_fails_without_creating_data(tmp_path):
    with pytest.raises(FileNotFoundError):
        acquire(tmp_path / "data", "2026-10-18", offline=True)
    assert not (tmp_path / "data").exists()


def test_portugal_download_failure_does_not_use_stale_data(tmp_path, monkeypatch):
    import requests
    from yieldcurves.sources import bportugal
    from test_benchmarks import snapshot as benchmarks_snapshot
    data = tmp_path / "data"
    save_snapshot(synthetic_csv(), data / "US")
    snapshot(data / "DE")
    (data / "PT").mkdir()
    benchmarks_snapshot(data / "PT")
    def failed(*args, **kwargs):
        raise requests.HTTPError("403 Forbidden")
    monkeypatch.setattr(bportugal, "download_snapshot", failed)
    result = run(data, tmp_path / "output", "2026-10-02",
                 fed_file=data / "US/feds200628.csv", germany_dir=data / "DE")
    assert not result["portugal_benchmarks"]["available"]
    assert "403" in result["acquisition_messages"][0]
    assert not (tmp_path / "output/PT_benchmarks").exists()
