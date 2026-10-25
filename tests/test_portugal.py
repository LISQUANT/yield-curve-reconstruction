"""Synthetic valuation fixtures test calibration, not Portuguese market results."""


import json

import numpy as np
import pandas as pd
import pytest

from yieldcurves.calibration import bond_prices, fit_prices
from yieldcurves.sources.portugal import load_panel
from yieldcurves.svensson import SvenssonParameters, spot_rate


@pytest.fixture
def panel():
    times = np.arange(1., 31.)
    maturities = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30]
    payments = np.zeros((len(maturities), len(times)))
    for i, maturity in enumerate(maturities):
        payments[i, :maturity] = 1 + i * 0.4
        payments[i, maturity-1] += 100
    params = SvenssonParameters(0.04, -0.02, 0.01, -0.01, 1, 5)
    prices = bond_prices(params, times, payments)
    return params, times, payments, prices


def write_panel(folder, panel):
    _, times, payments, prices = panel
    ids = [f"PTTEST{i:05d}0" for i in range(len(prices))]
    bonds = pd.DataFrame({"isin": ids, "observation_date": "2026-10-02",
                          "settlement_date": "2026-10-06", "currency": "EUR",
                          "issuer": "Republic of Portugal", "instrument_type": "nominal_fixed_rate",
                          "clean_price": prices-0.5, "accrued_interest": 0.5})
    flows = []
    for isin, row in zip(ids, payments):
        for time, amount in zip(times, row):
            if amount:
                payment = pd.Timestamp("2026-10-06") + pd.Timedelta(days=int(time*365))
                flows.append((isin, payment.date().isoformat(), amount))
    bonds.to_csv(folder / "bonds.csv", index=False)
    pd.DataFrame(flows, columns=["isin", "payment_date", "amount"]).to_csv(
        folder / "cashflows.csv", index=False)
    conventions = {"price_basis": "per_100_face", "curve_time_basis": "ACT/365F",
                   "cashflow_conventions": "Synthetic fixture only", "data_kind": "market_observations"}
    for name, value in conventions.items():
        bonds[name] = value
    bonds.to_csv(folder / "bonds.csv", index=False)
    return conventions



def test_coupon_prices_and_fit_recover_curve(panel):
    params, times, payments, prices = panel
    expected = np.sum(payments * np.exp(-times * spot_rate(times, params)), axis=1)
    np.testing.assert_allclose(prices, expected, atol=1e-12)
    fitted, diagnostics, starts = fit_prices(times, payments, prices)
    assert diagnostics["price_rmse"] < 1e-7
    np.testing.assert_allclose(spot_rate(times, fitted), spot_rate(times, params), atol=1e-7)
    assert len(starts) == 6 and starts.converged.any()


@pytest.mark.parametrize("problem", ["nan", "negative", "too_few", "missing_payment", "coverage"])
def test_calibration_rejects_invalid_panel(panel, problem):
    _, times, payments, prices = panel
    if problem == "nan":
        prices[0] = np.nan
    elif problem == "negative":
        payments[0, 0] = -1
    elif problem == "too_few":
        payments, prices = payments[:6], prices[:6]
    elif problem == "missing_payment":
        payments[0] = 0
    else:
        times = times + 5
    with pytest.raises(ValueError):
        fit_prices(times, payments, prices)


def test_import_preserves_dirty_price_units_and_cashflow_times(tmp_path, panel):
    write_panel(tmp_path, panel)
    bonds, matrix, _ = load_panel(tmp_path)
    np.testing.assert_allclose(bonds.clean_price + bonds.accrued_interest, panel[3])
    np.testing.assert_allclose(matrix.columns, panel[1])
    np.testing.assert_allclose(matrix, panel[2])


@pytest.mark.parametrize("problem", ["units", "date", "synthetic", "currency", "duplicate", "nan_date"])
def test_import_rejects_bad_conventions_or_panel(tmp_path, panel, problem):
    write_panel(tmp_path, panel)
    path = tmp_path / "bonds.csv"
    bonds = pd.read_csv(path)
    if problem == "units":
        bonds["price_basis"] = "cash_currency"
    elif problem == "date":
        bonds["settlement_date"] = "2026-09-30"
    elif problem == "synthetic":
        bonds["data_kind"] = "synthetic"
    elif problem == "nan_date":
        bonds["observation_date"] = "NaT"
    elif problem == "currency":
        bonds.loc[0, "currency"] = "USD"
    else:
        bonds.loc[1, "isin"] = bonds.loc[0, "isin"]
    bonds.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_panel(tmp_path)


def test_estimation_exports_separate_price_diagnostics(tmp_path, panel):
    from yieldcurves.portugal import estimate
    source = tmp_path / "input"
    source.mkdir()
    write_panel(source, panel)
    with pytest.raises(ValueError, match="match"):
        estimate(source, tmp_path / "wrong", "2026-10-01")
    output = tmp_path / "output"
    result = estimate(source, output, "2026-10-02")
    assert result["price_rmse"] < 1e-7
    curve = pd.read_csv(output / "curve.csv")
    assert curve.method.eq("bond_price_calibration").all()
    assert curve.settlement_date.eq("2026-10-06").all()
    assert (output / "calibration.pdf").read_bytes().startswith(b"%PDF")
    assert not (output / "validation.csv").exists()


def test_workflow_includes_imported_fit_without_mixing_validation(tmp_path, panel, monkeypatch):
    import socket
    from test_bundesbank import snapshot
    from test_fed import synthetic_csv
    from yieldcurves.sources.fed import save_snapshot
    from yieldcurves.workflow import run

    data = tmp_path / "data"
    data.mkdir()
    save_snapshot(synthetic_csv(), data / "US")
    snapshot(data / "DE")
    source = tmp_path / "portugal"
    source.mkdir()
    write_panel(source, panel)
    def no_network(*args, **kwargs):
        raise AssertionError("Offline mode opened a socket")
    monkeypatch.setattr(socket, "socket", no_network)
    output = tmp_path / "result"
    result = run(data, output, "2026-10-02", offline=True, portugal_dir=source)
    assert result["portugal_calibration"]["price_rmse"] < 1e-7
    assert set(result["validation"]) == {"US", "DE"}
    assert set(pd.read_csv(output / "curves.csv").country) == {"US", "DE"}
    assert (output / "PT/curve.csv").exists()
    assert not (output / "research_note.pdf").exists()


@pytest.mark.parametrize("format", ["legacy", "mixed", "matching"])
def test_optional_legacy_conventions_preserve_panel(tmp_path, panel, format):
    conventions = write_panel(tmp_path, panel)
    expected_bonds, expected_matrix, expected_meta = load_panel(tmp_path)
    path = tmp_path / "bonds.csv"
    bonds = pd.read_csv(path)
    omitted = list(conventions) if format == "legacy" else ["price_basis"] if format == "mixed" else []
    bonds.drop(columns=omitted).to_csv(path, index=False)
    conventions["source_url"] = "https://example.org/synthetic-test-panel"
    (tmp_path / "provenance.json").write_text(json.dumps(conventions))
    imported, matrix, meta = load_panel(tmp_path)
    pd.testing.assert_frame_equal(imported[expected_bonds.columns], expected_bonds)
    pd.testing.assert_frame_equal(matrix, expected_matrix)
    assert {key: meta[key] for key in expected_meta if key != "source_url"} == {
        key: value for key, value in expected_meta.items() if key != "source_url"}
    assert meta["source_url"] == conventions["source_url"]


@pytest.mark.parametrize("key", ["price_basis", "curve_time_basis", "cashflow_conventions",
                                 "data_kind", "observation_date", "settlement_date"])
def test_optional_legacy_conventions_reject_conflicts(tmp_path, panel, key):
    write_panel(tmp_path, panel)
    (tmp_path / "provenance.json").write_text(json.dumps({key: "conflicting value"}))
    with pytest.raises(ValueError, match="Conflicting convention"):
        load_panel(tmp_path)


@pytest.mark.parametrize("value", [None, "cash_currency"])
def test_legacy_fallback_keeps_price_unit_validation(tmp_path, panel, value):
    write_panel(tmp_path, panel)
    path = tmp_path / "bonds.csv"
    pd.read_csv(path).drop(columns=["price_basis"]).to_csv(path, index=False)
    (tmp_path / "provenance.json").write_text(json.dumps({"price_basis": value}))
    with pytest.raises(ValueError):
        load_panel(tmp_path)
