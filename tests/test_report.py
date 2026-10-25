"""The main command exports comparisons and preserves validation exceptions."""

from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from test_fed import synthetic_csv
from test_bundesbank import snapshot
from yieldcurves.sources.fed import save_snapshot
from yieldcurves.reconstruction import reconstruct


def test_saved_csv_requires_no_provenance(tmp_path):
    source = tmp_path / "source"
    save_snapshot(synthetic_csv(), source)
    output = tmp_path / "result"
    result = reconstruct(source / "feds200628.csv", "2026-10-02", output)
    assert result["validation_passed"] and result["reference_count"] == 30
    assert len(pd.read_csv(output / "curve.csv")) == 301
    with pytest.raises(FileExistsError):
        reconstruct(source / "feds200628.csv", "2026-10-02", output)


@pytest.mark.parametrize("raw", [b"<html>blocked</html>",
    synthetic_csv().replace(b"Continuously Compounded", b"Annual"),
    synthetic_csv().replace(b"2026-10-02", b"02/10/2026")])
def test_bad_source_fails_before_output(tmp_path, raw):
    source = tmp_path / "input.csv"
    source.write_bytes(raw)
    with pytest.raises(ValueError):
        reconstruct(source, "2026-10-02", tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_main_command_preserves_failed_comparison(tmp_path):
    data = tmp_path / "data"
    save_snapshot(synthetic_csv(), data / "US")
    snapshot(data / "DE")
    p = data / "DE/Y01.csv"
    p.write_bytes(p.read_bytes().replace(b"3.00", b"3.02"))
    output = tmp_path / "result"
    command = [sys.executable, "make_report.py", "--offline", "--data-dir", str(data),
               "--date", "2026-10-02", "--output-dir", str(output)]
    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2
    assert "validation exceptions" in result.stderr
    assert "DE: 29/30" in result.stdout
    assert not (output / "research_note.pdf").exists()
    assert set(pd.read_csv(output / "curves.csv").country) == {"US", "DE"}
