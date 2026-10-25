"""Estimate a Portuguese curve from an imported market panel."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil


from yieldcurves.calibration import bond_prices, fit_prices
from yieldcurves.sources.portugal import load_panel
from yieldcurves.reconstruction import curve_table
from yieldcurves.plots import plot_calibration


def estimate(folder, output, observation_date):
    bonds, matrix, provenance = load_panel(folder)
    if provenance["observation_date"] != observation_date:
        raise ValueError("Portuguese prices must match the selected US/German observation date.")
    times = matrix.columns.to_numpy(dtype=float)
    payments = matrix.to_numpy()
    prices = (bonds.clean_price + bonds.accrued_interest).to_numpy()
    parameters, diagnostics, starts = fit_prices(times, payments, prices)
    residuals = bonds.copy()
    residuals["dirty_price"] = prices
    residuals["model_dirty_price"] = bond_prices(parameters, times, payments)
    residuals["price_error_per_100"] = residuals.model_dirty_price - prices
    curve = curve_table(parameters, observation_date, "PT", "EUR", "continuous",
                        provenance["source_url"])
    curve["method"] = "bond_price_calibration"
    curve["data_kind"] = "market_estimation"
    curve["settlement_date"] = provenance["settlement_date"]
    low, high = diagnostics["maturity_range_years"]
    curve["outside_bond_maturity_range"] = ~curve.maturity_years.between(low, high)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name in ["bonds.csv", "cashflows.csv"]:
        shutil.copyfile(Path(folder) / name, output / name)
    curve.to_csv(output / "curve.csv", index=False)
    residuals.to_csv(output / "price_residuals.csv", index=False)
    starts.to_csv(output / "calibration_starts.csv", index=False)
    record = {"parameters": asdict(parameters), "beta_unit": "decimal", "tau_unit": "years",
              "compounding": "continuous", "time_origin": provenance["settlement_date"]}
    (output / "parameters.json").write_text(json.dumps(record, indent=2))
    diagnostics.update({"observation_date": observation_date,
                        "settlement_date": provenance["settlement_date"],
                        "bond_count": len(bonds), "data_kind": "market_estimation"})
    (output / "calibration.json").write_text(json.dumps(diagnostics, indent=2, allow_nan=False))

    plot_calibration(curve, residuals, times, payments, provenance, observation_date,
                     low, high, output / "calibration")
    return diagnostics
