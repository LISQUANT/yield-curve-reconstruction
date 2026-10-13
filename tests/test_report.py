"""Offline orchestration checks use labelled synthetic input fixtures."""

from hashlib import sha256
import json
import socket
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from make_report import reconstruct
from test_fed import synthetic_csv
from yieldcurves.sources.fed import save_snapshot


def test_offline_outputs_and_provenance(tmp_path, monkeypatch):
    source = tmp_path / "raw"
    save_snapshot(synthetic_csv(), source, acquisition="synthetic test fixture")

    def no_network(*args, **kwargs):
        raise AssertionError("Offline mode attempted network access")

    monkeypatch.setattr(socket, "socket", no_network)
    output = tmp_path / "result"
    result = reconstruct(source / "feds200628.csv", source / "provenance.json",
                         "2026-10-12", output)
    assert result["validation_passed"] and result["reference_count"] == 30
    assert result["country_status"]["DE"] == "not implemented"
    assert len(pd.read_csv(output / "curve.csv")) == 301
    for name, digest in result["output_sha256"].items():
        assert sha256((output / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        reconstruct(source / "feds200628.csv", source / "provenance.json",
                    "2026-10-12", output)


@pytest.mark.parametrize("key,value", [("sha256", "0" * 64),
    ("native_compounding", "annual"), ("source_url", "https://example.com/data")])
def test_bad_provenance_fails_before_output(tmp_path, key, value):
    source = tmp_path / "raw"
    meta = save_snapshot(synthetic_csv(), source, acquisition="synthetic test fixture")
    meta[key] = value
    (source / "provenance.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        reconstruct(source / "feds200628.csv", source / "provenance.json",
                    "2026-10-12", tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_failed_reference_cli_keeps_diagnostics_and_exits_nonzero(tmp_path):
    source = tmp_path / "raw"
    # Alter quoted spot references, not the higher-precision flat beta value.
    raw = synthetic_csv().replace(b",3.0000,", b",3.0100,")
    save_snapshot(raw, source, acquisition="synthetic test fixture")
    output = tmp_path / "result"
    command = [sys.executable, "make_report.py", "--snapshot",
               str(source / "feds200628.csv"), "--provenance",
               str(source / "provenance.json"), "--date", "2026-10-12",
               "--output-dir", str(output)]
    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "precision-derived tolerance" in result.stderr
    assert not json.loads((output / "manifest.json").read_text())["validation_passed"]


def test_cli_rejects_unsupported_country():
    result = subprocess.run([sys.executable, "make_report.py", "--country", "DE"],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
