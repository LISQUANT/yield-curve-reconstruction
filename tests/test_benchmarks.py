"""Synthetic benchmark quotes test segregation, provenance and smoothing."""

from hashlib import sha256
import json

import numpy as np
import pandas as pd
import pytest

from yieldcurves import benchmarks


def snapshot(folder):
    years = np.array([2, 3, 5, 7, 10, 15, 20, 30.])
    frame = pd.DataFrame({"country": "PT", "currency": "EUR",
                          "observation_date": "2026-10-02", "maturity_years": years,
                          "yield_percent": benchmarks.shape(years, [4, -1, 0.5, 3]),
                          "source_url": "https://example.invalid/synthetic-fixture",
                          "retrieved_at_utc": "2026-10-18T12:00:00Z",
                          "quantity": "benchmark_yield_observation"})
    frame.iloc[::-1].to_csv(folder / "observations.csv", index=False)
    meta = {"sha256": sha256((folder / "observations.csv").read_bytes()).hexdigest(),
            "usage_permission": "Synthetic test fixture; no market data.",
            "quote_convention": "Synthetic percentage benchmark yield."}
    (folder / "provenance.json").write_text(json.dumps(meta))
    return frame, meta


def test_snapshot_sorts_preserves_units_and_does_not_fill_dates(tmp_path):
    expected, _ = snapshot(tmp_path)
    result, _ = benchmarks.read_snapshot(tmp_path, "2026-10-02")
    np.testing.assert_allclose(result.yield_percent, expected.yield_percent)
    assert result.maturity_years.is_monotonic_increasing
    assert benchmarks.read_snapshot(tmp_path, "2026-10-01")[0] is None


@pytest.mark.parametrize("column,value", [
    ("currency", "USD"), ("country", "DE"), ("observation_date", "2026-10-01"),
    ("quantity", "zero_coupon_spot"), ("maturity_years", 0), ("maturity_years", 1000),
    ("maturity_years", 3), ("yield_percent", np.nan), ("yield_percent", np.inf),
    ("source_url", "missing"), ("retrieved_at_utc", "2026-01-01T00:00:00Z")])
def test_snapshot_rejects_invalid_values(tmp_path, column, value):
    frame, meta = snapshot(tmp_path)
    frame.loc[0, column] = value
    frame.to_csv(tmp_path / "observations.csv", index=False)
    meta["sha256"] = sha256((tmp_path / "observations.csv").read_bytes()).hexdigest()
    (tmp_path / "provenance.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        benchmarks.read_snapshot(tmp_path, "2026-10-02")


def test_hash_and_permission_required(tmp_path):
    _, meta = snapshot(tmp_path)
    meta["usage_permission"] = ""
    (tmp_path / "provenance.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="permission"):
        benchmarks.read_snapshot(tmp_path, "2026-10-02")
    snapshot(tmp_path)
    with (tmp_path / "observations.csv").open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="checksum"):
        benchmarks.read_snapshot(tmp_path, "2026-10-02")


def test_smoothing_is_separate_from_zero_rate_functions(tmp_path, monkeypatch):
    from yieldcurves import svensson, reconstruction, calibration
    def forbidden(*args, **kwargs):
        raise AssertionError("Benchmark yields reached a zero-curve or pricing function.")
    for module, names in [(svensson, ["spot_rate", "discount_factor", "instantaneous_forward"]),
                          (reconstruction, ["curve_table"]), (calibration, ["fit_prices", "bond_prices"])]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    folder = tmp_path / "source"
    folder.mkdir()
    snapshot(folder)
    result = benchmarks.export_snapshot(folder, tmp_path / "output", "2026-10-02")
    assert result["method"] == "NS"
    assert result["display_rmse_bp"] < 1e-5
    assert result["diagnostic_fits"][0]["interior_leave_one_out_max_change_bp"] < 1e-3
    curve = pd.read_csv(tmp_path / "output/indicative_curve.csv")
    assert curve.maturity_years.min() == 2 and curve.maturity_years.max() == 30
    assert "discount_factor" not in curve and "spot_rate_decimal" not in curve
    assert curve.quantity.eq("indicative_benchmark_fit").all()


def test_unidentified_flat_curve_uses_connected_observations(tmp_path):
    frame, _ = snapshot(tmp_path)
    frame["yield_percent"] = 3.0
    curve, residuals, result = benchmarks.fit_benchmarks(frame)
    assert result["method"] == "connected_observations"
    assert "identity" in result["residual_note"]
    np.testing.assert_allclose(curve.yield_percent, 3)
    assert residuals.display_minus_observed_bp.eq(0).all()


def test_sparse_panel_does_not_force_six_parameters(tmp_path):
    frame, _ = snapshot(tmp_path)
    _, _, result = benchmarks.fit_benchmarks(frame.iloc[[0, 2, 4, 7]])
    assert result["method"] == "connected_observations"
    assert all(not fit["eligible"] for fit in result["diagnostic_fits"])


def test_unstable_exclusion_rejects_smooth_fit(tmp_path, monkeypatch):
    frame, _ = snapshot(tmp_path)
    original = benchmarks._fit
    def unstable(years, yields, model):
        fits = original(years, yields, model)
        if len(years) < len(frame):
            for fit in fits:
                fit.x[0] += 0.2
        return fits
    monkeypatch.setattr(benchmarks, "_fit", unstable)
    _, _, result = benchmarks.fit_benchmarks(frame)
    assert result["method"] == "connected_observations"
    assert result["diagnostic_fits"][0]["interior_leave_one_out_max_change_bp"] > 5
