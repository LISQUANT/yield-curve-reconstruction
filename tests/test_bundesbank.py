"""Parser fixtures are synthetic; official reference checks are separate."""

import csv
from hashlib import sha256
from io import BytesIO, StringIO
import json

import numpy as np
import pandas as pd
import pytest

from yieldcurves.sources import bundesbank as b
from yieldcurves.svensson import continuous_rate, discount_factor, spot_rate
from yieldcurves.workflow import common_date
from test_fed import synthetic_csv
from yieldcurves.sources import fed


def series_bytes(key, rows=None):
    output = StringIO()
    writer = csv.writer(output)
    series = "BBSIS." + b.SERIES[key]
    decimals = 5 if key in b.PARAMETERS else 2
    value = "3.00000" if key == "BETA0" else "1.00000" if key.startswith("TAU") else "0.00000"
    if key.startswith("Y"):
        value = "3.00"
    writer.writerows([["", series, series + "_FLAGS"], ["", "Synthetic fixture", ""],
                      ["Decimals", decimals, ""], ["Time format code", "P1D", ""],
                      ["last update", "2026-10-18", ""]])
    writer.writerows(rows or [["2026-10-02", value, ""],
                             ["2026-10-03", ".", "No value available"]])
    return output.getvalue().encode()


def snapshot(folder):
    folder.mkdir()
    meta = {"native_compounding": "annual", "rate_unit": "percent", "tau_unit": "years",
            "acquisition": "synthetic test fixture", "files": {}}
    for key, series in b.SERIES.items():
        raw = series_bytes(key)
        (folder / (key + ".csv")).write_bytes(raw)
        meta["files"][key + ".csv"] = {"sha256": sha256(raw).hexdigest(),
                                        "series_id": "BBSIS." + series,
                                        "source_url": b.API + series + "?format=csv"}
    (folder / "provenance.json").write_text(json.dumps(meta))
    return folder


def test_flat_curve_units_and_annual_discounting(tmp_path):
    frame, _ = b.load_snapshot(snapshot(tmp_path / "de"))
    row = frame.loc["2026-10-02"]
    p = b.normalize_parameters(row)
    assert p.beta0 == 0.03 and p.tau1 == 1
    result = b.validate_reconstruction(row)
    assert len(result) == 30 and result.within_tolerance.all()
    np.testing.assert_allclose(result.error_bp, 0)
    assert discount_factor(10, p, compounding="annual") == pytest.approx(1.03 ** -10)
    assert continuous_rate(spot_rate(10, p), "annual") == pytest.approx(np.log1p(0.03))


@pytest.mark.parametrize("raw", [b"<html>unavailable</html>",
    series_bytes("Y01").replace(b"ZST.ZI", b"ZAR.ZI"),
    series_bytes("Y01").replace(b"Decimals,2", b"Decimals,3"),
    series_bytes("Y01").replace(b"P1D", b"P1M"),
    series_bytes("Y01", [["2026-10-02", "nan", ""]]),
    series_bytes("Y01", [["2026-10-02", "3.00", "provisional"]]),
    series_bytes("Y01", [["2026-10-02", "3.000", ""]]),
    series_bytes("Y01", [["2026-10-02", "3.00", ""], ["2026-10-02", "3.00", ""]]),
])
def test_reject_wrong_or_ambiguous_data(raw):
    with pytest.raises(ValueError):
        b.read_series(raw, "Y01")


def test_missing_dates_not_filled(tmp_path):
    frame, _ = b.load_snapshot(snapshot(tmp_path / "de"))
    assert list(b.complete_dates(frame)) == [pd.Timestamp("2026-10-02")]
    frame.loc["2026-10-02", "TAU2"] = "0.00000"
    assert b.complete_dates(frame).empty


def test_hash_and_wrong_series_identity(tmp_path):
    folder = snapshot(tmp_path / "de")
    p = folder / "Y01.csv"
    p.write_bytes(p.read_bytes().replace(b"3.00", b"4.00"))
    with pytest.raises(ValueError, match="checksum"):
        b.load_snapshot(folder)


def test_common_date_precedes_missing_latest(tmp_path):
    frame, _ = b.load_snapshot(snapshot(tmp_path / "de"))
    us = fed.read_fed_csv(synthetic_csv())
    assert common_date(us, frame, "2026-10-18") == "2026-10-02"
    with pytest.raises(ValueError, match="No complete common"):
        common_date(us, frame, "2026-10-01")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        common_date(us, frame, "02/10/2026")


def test_download_validates_response(monkeypatch):
    calls = []
    def fetch(url, timeout):
        calls.append((url, timeout))
        return BytesIO(series_bytes("BETA0"))
    monkeypatch.setattr(b, "urlopen", fetch)
    raw, url = b.download_series("BETA0", "2026-10-01")
    assert raw == series_bytes("BETA0") and calls == [(url, 30)]
    monkeypatch.setattr(b, "urlopen", lambda *a, **k: BytesIO(b"<html>blocked</html>"))
    with pytest.raises(ValueError):
        b.download_series("BETA0", "2026-10-01")


def test_wrong_reference_remains_failure(tmp_path):
    frame, _ = b.load_snapshot(snapshot(tmp_path / "de"))
    row = frame.loc["2026-10-02"].copy()
    row["Y01"] = "3.02"
    result = b.validate_reconstruction(row)
    assert not result.within_tolerance.iloc[0]
    assert result.error_bp.iloc[0] == pytest.approx(-2)
    assert result.tolerance_bp.iloc[0] < 0.51
