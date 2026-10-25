"""Read the Fed nominal CSV and reconstruct continuous zero-coupon rates."""

import csv
import argparse
from decimal import Decimal
from io import StringIO
from pathlib import Path
import re
import requests

import numpy as np
import pandas as pd

from yieldcurves.svensson import SvenssonParameters, spot_rate
from yieldcurves.validation import compare_spot_rates, parameter_rounding_bound

SOURCE_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
PARAMETERS = ["BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]
REFERENCES = [f"SVENY{year:02d}" for year in range(1, 31)]
MISSING = {"", "NA", "N/A", "ND", "."}


def read_fed_csv(raw):
    """Read the CSV and keep the original numeric precision."""
    lines = raw.decode("utf-8-sig").splitlines()
    headers = [i for i, line in enumerate(lines) if line.startswith("Date,")]
    if len(headers) != 1:
        raise ValueError("Expected one Fed Date header, after the CSV preamble.")
    start = headers[0]
    if "Zero-coupon yield,Continuously Compounded,SVENYXX" not in lines[:start]:
        raise ValueError("Fed preamble does not establish continuous SVENY rates.")
    rows = list(csv.reader(StringIO("\n".join(lines[start:]))))
    columns = rows[0]
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate CSV columns.")
    if not set(["Date"] + PARAMETERS + REFERENCES).issubset(columns):
        raise ValueError("Missing required Fed parameter or SVENY columns.")
    data = [row for row in rows[1:] if row]
    if not data or any(len(row) != len(columns) for row in data):
        raise ValueError("Empty or malformed Fed data rows.")
    frame = pd.DataFrame(data, columns=columns)
    if not frame.Date.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Fed dates must be YYYY-MM-DD.")
    frame["Date"] = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    if frame.Date.duplicated().any():
        raise ValueError("Duplicate observation dates.")
    for column in PARAMETERS + REFERENCES:
        tokens = frame[column].str.strip()
        pd.to_numeric(tokens.mask(tokens.isin(MISSING)), errors="raise")
        frame[column] = tokens
    return frame.sort_values("Date").reset_index(drop=True)


def select_complete_date(frame, requested_date):
    """Select the latest complete row up to the cutoff date."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(requested_date)):
        raise ValueError("Requested date must be YYYY-MM-DD.")
    cutoff = pd.Timestamp(requested_date)
    if pd.isna(cutoff) or cutoff.tzinfo is not None:
        raise ValueError("Requested date must be a timezone-free calendar date.")
    candidates = frame.loc[frame.Date.isin(complete_dates(frame)) & frame.Date.le(cutoff)]
    if candidates.empty:
        raise ValueError("No complete post-1979 NSS date with all 30 SVENY rates.")
    return candidates.iloc[-1]


def complete_dates(frame):
    values = frame[PARAMETERS + REFERENCES].replace(
        dict.fromkeys(MISSING, np.nan)).astype(float)
    valid = np.isfinite(values).all(axis=1)
    valid &= (values.TAU1 > 0) & (values.TAU2 > 0) & frame.Date.ge("1980-01-01")
    return pd.DatetimeIndex(frame.loc[valid, "Date"])


def normalize_parameters(row):
    """Convert beta percentages to decimals, leaving tau values in years."""
    values = [float(row[name]) for name in PARAMETERS]
    return SvenssonParameters(*[value / 100 for value in values[:4]], *values[4:])


def validate_reconstruction(row):
    """Compare all 30 spots with a precision-derived per-maturity tolerance."""
    years = np.arange(1, 31, dtype=float)
    references = np.array([float(row[name]) / 100 for name in REFERENCES])
    if any(Decimal(row[name]) != Decimal(row[name]).quantize(Decimal("0.0001"))
           for name in REFERENCES):
        raise ValueError("SVENY precision changed; review the rounding policy.")
    observed = pd.DataFrame({
        "country": "US", "observation_date": row.Date.date().isoformat(),
        "maturity_years": years, "compounding": "continuous",
        "spot_rate_decimal": references,
    })
    model = observed.copy()
    model["spot_rate_decimal"] = spot_rate(years, normalize_parameters(row))
    result = compare_spot_rates(observed, model, tolerance_bp=0)
    result["reference_series_id"] = REFERENCES
    result["reference_rounding_bp"] = 0.005
    result["parameter_rounding_bound_bp"] = parameter_rounding_bound(row, years)
    result["numerical_allowance_bp"] = 1e-9
    result["tolerance_bp"] = (result.reference_rounding_bp
                              + result.parameter_rounding_bound_bp
                              + result.numerical_allowance_bp)
    result["within_tolerance"] = result.error_bp.abs() <= result.tolerance_bp
    return result


def download_csv(*, timeout=30):
    """Request the official file and validate its format before use."""
    response = requests.get(SOURCE_URL, timeout=timeout)
    response.raise_for_status()
    raw = response.content
    read_fed_csv(raw)
    return raw


def save_snapshot(raw, output):
    """Save a validated CSV without requiring a sidecar manifest."""
    frame = read_fed_csv(raw)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "feds200628.csv").write_bytes(raw)
    return frame


def import_snapshot(source, output):
    return save_snapshot(Path(source).read_bytes(), output)


def main():
    parser = argparse.ArgumentParser(description="Download or import the official Fed CSV.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true")
    mode.add_argument("--import-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = download_csv() if args.download else args.import_file.read_bytes()
        save_snapshot(raw, args.output_dir)
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Fed acquisition failed: {exc}\n")


if __name__ == "__main__":
    main()
