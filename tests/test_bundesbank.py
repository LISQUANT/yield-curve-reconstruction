"""Parser fixtures are synthetic; official reference checks are separate."""

import csv
from io import StringIO
from types import SimpleNamespace

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
    for key in b.SERIES:
        (folder / (key + ".csv")).write_bytes(series_bytes(key))
    return folder


def test_flat_curve_units_and_annual_discounting(tmp_path):
    frame = b.load_snapshot(snapshot(tmp_path / "de"))
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
    frame = b.load_snapshot(snapshot(tmp_path / "de"))
    assert list(b.complete_dates(frame)) == [pd.Timestamp("2026-10-02")]
    frame.loc["2026-10-02", "TAU2"] = "0.00000"
    assert b.complete_dates(frame).empty


def test_saved_wrong_series_identity_rejected(tmp_path):
    folder = snapshot(tmp_path / "de")
    (folder / "Y01.csv").write_bytes(series_bytes("Y02"))
    with pytest.raises(ValueError, match="series"):
        b.load_snapshot(folder)


def test_common_date_precedes_missing_latest(tmp_path):
    frame = b.load_snapshot(snapshot(tmp_path / "de"))
    us = fed.read_fed_csv(synthetic_csv())
    assert common_date(us, frame, "2026-10-18") == "2026-10-02"
    with pytest.raises(ValueError, match="No complete common"):
        common_date(us, frame, "2026-10-01")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        common_date(us, frame, "02/10/2026")


def test_download_validates_response_and_date_filter(monkeypatch):
    calls = []
    def fetch(url, params, timeout):
        calls.append((url, params, timeout))
        return SimpleNamespace(content=series_bytes("BETA0"), url=url, raise_for_status=lambda: None)
    monkeypatch.setattr(b.requests, "get", fetch)
    raw, url = b.download_series("BETA0", "2026-10-01", "2026-10-02")
    assert raw == series_bytes("BETA0")
    assert calls == [(url, {"format": "csv", "lang": "en", "startPeriod": "2026-10-01", "endPeriod": "2026-10-02"}, 30)]
    monkeypatch.setattr(b.requests, "get", lambda *a, **k:
                        SimpleNamespace(content=b"<html>blocked</html>", url=url, raise_for_status=lambda: None))
    with pytest.raises(ValueError):
        b.download_series("BETA0", "2026-10-01")


def test_wrong_reference_remains_failure(tmp_path):
    frame = b.load_snapshot(snapshot(tmp_path / "de"))
    row = frame.loc["2026-10-02"].copy()
    row["Y01"] = "3.02"
    result = b.validate_reconstruction(row)
    assert not result.within_tolerance.iloc[0]
    assert result.error_bp.iloc[0] == pytest.approx(-2)
    assert result.tolerance_bp.iloc[0] < 0.51
