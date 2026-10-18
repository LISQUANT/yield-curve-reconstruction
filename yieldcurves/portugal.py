"""Estimate a Portuguese curve from an imported market panel."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil

import numpy as np

from yieldcurves.calibration import bond_prices, fit_prices
from yieldcurves.sources.portugal import load_panel
from yieldcurves.reconstruction import curve_table
from yieldcurves.plots import save_figure


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
    for name in ["bonds.csv", "cashflows.csv", "provenance.json"]:
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

    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(6.4, 4.5), layout="constrained")
    axes[0].plot(curve.maturity_years, curve.spot_rate_decimal * 100, color="#800020")
    axes[0].axvspan(0, low, color="grey", alpha=0.12, label="Outside bond maturity range")
    if high < 30:
        axes[0].axvspan(high, 30, color="grey", alpha=0.12)
    axes[0].set(ylabel="Continuous spot (% p.a.)", xlabel="Years from settlement",
                title=f"Portugal | Prices {observation_date} | Settlement {provenance['settlement_date']}")
    axes[0].legend(frameon=False, fontsize=8)
    maturities = np.max(np.where(payments > 0, times, 0), axis=1)
    axes[1].scatter(maturities, residuals.price_error_per_100, color="#800020")
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set(xlabel="Bond maturity (years from settlement)", ylabel="Price error per 100")
    save_figure(fig, output / "calibration")
    return diagnostics
