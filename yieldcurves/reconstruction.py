"""Reconstruct published curves and compare matching native spot rates."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

from yieldcurves.plots import plot_fed_curve
from yieldcurves.svensson import (
    continuous_rate, discount_factor, instantaneous_forward, spot_rate,
)
from yieldcurves.sources import fed, bundesbank


def reconstruct(snapshot, requested_date, output):
    frame = fed.read_fed_csv(Path(snapshot).read_bytes())
    row = fed.select_complete_date(frame, requested_date)
    parameters = fed.normalize_parameters(row)
    validation = fed.validate_reconstruction(row)
    date = row.Date.date().isoformat()
    curve = curve_table(parameters, date, "US", "USD", "continuous", "Fed_GSW")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    curve.to_csv(output / "curve.csv", index=False)
    validation.to_csv(output / "validation.csv", index=False)
    record = {"observation_date": date, "parameters": asdict(parameters),
              "source_parameter_tokens": {name: row[name] for name in fed.PARAMETERS},
              "beta_unit": "decimal", "tau_unit": "years", "compounding": "continuous"}
    (output / "parameters.json").write_text(json.dumps(record, indent=2))
    plot_fed_curve(curve, validation, output / "curve.png")
    return {"observation_date": date, "currency": "USD", "native_compounding": "continuous",
            **error_summary(validation)}


def curve_table(parameters, date, country, currency, compounding, source):
    years = np.linspace(0, 30, 301)
    native = spot_rate(years, parameters)
    curve = pd.DataFrame({
        "country": country, "currency": currency, "observation_date": date,
        "maturity_years": years, "native_compounding": compounding,
        "spot_rate_decimal": native,
        "spot_rate_continuous_decimal": continuous_rate(native, compounding),
        "discount_factor": discount_factor(years, parameters, compounding=compounding),
        "forward_rate_continuous_decimal": instantaneous_forward(
            years, parameters, compounding=compounding),
        "method": "published_parameter_reconstruction",
        "quantity": "zero_coupon_spot",
        "source_id": source, "data_kind": "institutional_reconstruction",
    })
    columns = ["spot_rate_decimal", "spot_rate_continuous_decimal",
               "discount_factor", "forward_rate_continuous_decimal"]
    if not np.isfinite(curve[columns]).all().all() or (curve.discount_factor <= 0).any():
        raise ValueError("Curve evaluation produced non-finite rates or invalid discounts.")
    return curve


def error_summary(validation):
    errors = validation.error_bp
    return {
        "reference_count": len(validation),
        "passed_count": int(validation.within_tolerance.sum()),
        "validation_passed": bool(validation.within_tolerance.all()),
        "max_absolute_error_bp": float(errors.abs().max()),
        "mean_absolute_error_bp": float(errors.abs().mean()),
        "rmse_bp": float(np.sqrt(np.mean(errors ** 2))),
    }


def reconstruct_germany(frame, date, output):
    row = frame.loc[pd.Timestamp(date)]
    parameters = bundesbank.normalize_parameters(row)
    validation = bundesbank.validate_reconstruction(row)
    curve = curve_table(parameters, date, "DE", "EUR", "annual", "Bundesbank_BBSIS")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    curve.to_csv(output / "curve.csv", index=False)
    validation.to_csv(output / "validation.csv", index=False)
    record = {"observation_date": date, "parameters": asdict(parameters),
              "beta_unit": "decimal", "tau_unit": "years", "compounding": "annual",
              "source_parameter_tokens": {k: row[k] for k in bundesbank.PARAMETERS}}
    (output / "parameters.json").write_text(json.dumps(record, indent=2))
    summary = {"observation_date": date, "currency": "EUR",
               "native_compounding": "annual", **error_summary(validation)}
    return summary
