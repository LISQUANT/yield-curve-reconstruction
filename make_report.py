"""Reconstruct one US date from a saved official Fed CSV, without network access."""

import argparse
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
from yieldcurves.svensson import discount_factor, instantaneous_forward, spot_rate
from yieldcurves.sources.fed import (
    PARAMETERS, SOURCE_URL, normalize_parameters, read_fed_csv,
    select_complete_date, validate_reconstruction,
)


def reconstruct(snapshot, provenance_path, requested_date, output):
    """Write a new result directory; return a manifest even when validation fails."""
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
    years = np.linspace(0, 30, 301)
    curve = pd.DataFrame({
        "country": "US", "currency": "USD", "observation_date": date,
        "maturity_years": years, "native_compounding": "continuous",
        "spot_rate_decimal": spot_rate(years, parameters),
        "discount_factor": discount_factor(years, parameters, compounding="continuous"),
        "forward_rate_continuous_decimal": instantaneous_forward(
            years, parameters, compounding="continuous"),
        "method": "published_parameter_reconstruction",
        "source_id": "Fed_GSW", "data_kind": "institutional_reconstruction",
    })
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
    code_root = Path(__file__).resolve().parent
    code_files = ["yieldcurves/svensson.py", "yieldcurves/validation.py",
                  "yieldcurves/sources/fed.py", "make_report.py", "yieldcurves/plots.py"]
    summary = {
        "data_kind": "institutional_reconstruction", "offline": True,
        "country_status": {"US": "reconstructed", "DE": "not implemented"},
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", choices=["US"], default="US",
                        help="US only; Germany is pending implementation.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--date", required=True, help="Latest permissible date (YYYY-MM-DD).")
    parser.add_argument("--output-dir", type=Path, required=True, help="New run directory.")
    args = parser.parse_args()
    try:
        result = reconstruct(args.snapshot, args.provenance, args.date, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Fed reconstruction failed: {exc}\n")
    print(json.dumps(result, indent=2))
    if not result["validation_passed"]:
        raise SystemExit("Fed reconstruction failed its precision-derived tolerance.")


if __name__ == "__main__":
    main()
