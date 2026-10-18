"""Reconstruct one US date from a saved official Fed CSV, without network access."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform

import matplotlib
import numpy as np
import pandas as pd

from yieldcurves.plots import plot_fed_curve
from yieldcurves.svensson import (
    continuous_rate, discount_factor, instantaneous_forward, spot_rate,
)
from yieldcurves.sources.fed import (
    PARAMETERS, SOURCE_URL, normalize_parameters, read_fed_csv,
    select_complete_date, validate_reconstruction,
)


def reconstruct(snapshot, provenance_path, requested_date, output):
    """Save the curve, comparison and validation result in a new folder."""
    raw = Path(snapshot).read_bytes()
    provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
    required = {"source_url", "retrieved_at_utc", "sha256", "acquisition",
                "native_compounding", "rate_unit", "tau_unit", "universe"}
    if not required.issubset(provenance):
        raise ValueError("Incomplete snapshot provenance.")
    if provenance["sha256"] != sha256(raw).hexdigest():
        raise ValueError("Snapshot checksum does not match provenance.")
    if provenance["source_url"] != SOURCE_URL:
        raise ValueError("Expected the official Fed nominal CSV source URL.")
    if (provenance["native_compounding"], provenance["rate_unit"],
            provenance["tau_unit"]) != ("continuous", "percent", "years"):
        raise ValueError("Unexpected source units or compounding.")
    frame = read_fed_csv(raw)
    row = select_complete_date(frame, requested_date)
    parameters = normalize_parameters(row)
    validation = validate_reconstruction(row)
    date = row.Date.date().isoformat()
    curve = curve_table(parameters, date, "US", "USD", "continuous", "Fed_GSW")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    curve.to_csv(output / "curve.csv", index=False)
    validation.to_csv(output / "validation.csv", index=False)
    parameter_record = {
        "observation_date": date, "parameters": asdict(parameters),
        "source_parameter_tokens": {name: row[name] for name in PARAMETERS},
        "beta_unit": "decimal", "tau_unit": "years", "compounding": "continuous",
    }
    (output / "parameters.json").write_text(json.dumps(parameter_record, indent=2))
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2))
    plot_fed_curve(curve, validation, output / "curve.png")
    code_root = Path(__file__).resolve().parents[1]
    code_files = ["yieldcurves/svensson.py", "yieldcurves/validation.py",
                  "yieldcurves/sources/fed.py", "yieldcurves/reconstruction.py", "yieldcurves/plots.py"]
    summary = {
        "data_kind": "institutional_reconstruction", "offline": True,
        "country_status": {"US": "reconstructed", "DE": "not requested by the US-only entry point"},
        "requested_date": requested_date, "observation_date": date,
        "date_policy": "latest complete post-1979 NSS date on/before cutoff",
        "snapshot_first_date": frame.Date.min().date().isoformat(),
        "snapshot_last_date": frame.Date.max().date().isoformat(),
        "snapshot_rows": len(frame), "raw_sha256": provenance["sha256"],
        "source_url": SOURCE_URL, "universe": provenance["universe"],
        "currency": "USD", "native_compounding": "continuous",
        "reference_count": len(validation), "grid_count": len(curve),
        "reference_range_years": [1, 30], "grid_range_years": [0, 30],
        "grid_note": "Below 1 year is model extrapolation, not SVENY validation.",
        "max_absolute_error_bp": float(validation.error_bp.abs().max()),
        "mean_absolute_error_bp": float(validation.error_bp.abs().mean()),
        "rmse_bp": float(np.sqrt(np.mean(validation.error_bp ** 2))),
        "max_parameter_rounding_bound_bp": float(
            validation.parameter_rounding_bound_bp.max()),
        "validation_passed": bool(validation.within_tolerance.all()),
        "tolerance_policy": "0.005 bp reference rounding + parameter bound + 1e-9 bp",
        "interpretation": "Reconstruction agreement; not independent bond-price fit.",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "pandas": pd.__version__, "matplotlib": matplotlib.__version__},
        "code_sha256": {p: sha256((code_root / p).read_bytes()).hexdigest()
                        for p in code_files},
        "output_sha256": {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in output.iterdir() if p.is_file()},
    }
    (output / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary




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


def reconstruct_germany(frame, provenance, date, output):
    from yieldcurves.sources import bundesbank

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
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2))
    summary = {"observation_date": date, "currency": "EUR",
               "native_compounding": "annual", **error_summary(validation)}
    (output / "manifest.json").write_text(json.dumps(summary, indent=2))
    return summary
