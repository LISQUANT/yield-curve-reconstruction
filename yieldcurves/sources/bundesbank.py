"""Daily German federal-security spot rates and Svensson parameters."""

import csv
from io import StringIO
from pathlib import Path
import re
import requests

import numpy as np
import pandas as pd

from yieldcurves.svensson import SvenssonParameters, spot_rate
from yieldcurves.validation import compare_spot_rates, parameter_rounding_bound

SOURCE_PAGE = (
    "https://www.bundesbank.de/en/statistics/money-and-capital-markets/"
    "interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570"
)
API = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
PARAMETERS = ["BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]
SERIES = {
    name: f"D.I.ZST.{code}.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A"
    for name, code in zip(PARAMETERS, ["B0", "B1", "B2", "B3", "T1", "T2"])
}
SERIES.update({
    f"Y{year:02d}": f"D.I.ZST.ZI.EUR.S1311.B.A604.R{year:02d}XX.R.A.A._Z._Z.A"
    for year in range(1, 31)
})


def read_series(raw, key):
    """Validate one official CSV, preserving its printed precision."""
    rows = list(csv.reader(StringIO(raw.decode("utf-8-sig"))))
    series_id = "BBSIS." + SERIES[key]
    if not rows or rows[0] != ["", series_id, series_id + "_FLAGS"]:
        raise ValueError(f"Unexpected Bundesbank series: {key}")
    if any(len(row) != 3 for row in rows):
        raise ValueError("Malformed Bundesbank CSV row.")
    metadata = {row[0]: row[1] for row in rows[1:]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0])}
    decimals = 5 if key in PARAMETERS else 2
    if metadata.get("Decimals") != str(decimals):
        raise ValueError("Bundesbank precision changed; review rounding assumptions.")
    if metadata.get("Time format code") != "P1D":
        raise ValueError("Expected daily Bundesbank data.")
    if metadata.get("unit multiplier", "One") != "One":
        raise ValueError("Unexpected Bundesbank unit multiplier.")
    if key.startswith("Y") and metadata.get("unit", "Prozent") not in {"Prozent", "Percent"}:
        raise ValueError("Expected percentage Bundesbank spot rates.")
    observations = [row for row in rows[1:]
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0])]
    if not observations:
        raise ValueError("No daily observations in Bundesbank CSV.")
    frame = pd.DataFrame(observations, columns=["Date", key, "flag"])
    frame["Date"] = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    if frame.Date.duplicated().any():
        raise ValueError("Duplicate Bundesbank dates.")
    missing = frame[key].isin([".", ""])
    if ((frame.flag != "") & ~missing).any():
        raise ValueError("Flagged Bundesbank values require manual review.")
    tokens = frame.loc[~missing, key]
    values = pd.to_numeric(tokens, errors="raise")
    if not np.isfinite(values).all():
        raise ValueError("Non-finite Bundesbank values.")
    if not tokens.str.fullmatch(rf"-?\d+\.\d{{{decimals}}}").all():
        raise ValueError("Unexpected printed precision in Bundesbank values.")
    frame.loc[missing, key] = np.nan
    return frame.set_index("Date")[key].sort_index()


def download_series(key, start_date, end_date=None):
    pd.to_datetime(start_date, format="%Y-%m-%d", errors="raise")
    params = {"format": "csv", "lang": "en", "startPeriod": start_date}
    if end_date is not None:
        pd.to_datetime(end_date, format="%Y-%m-%d", errors="raise")
        params["endPeriod"] = end_date
    response = requests.get(API + SERIES[key], params=params, timeout=30)
    response.raise_for_status()
    read_series(response.content, key)
    return response.content, response.url


def download_snapshot(output, start_date, end_date=None):
    """Download the 36 series for a bounded date interval."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for key in SERIES:
        raw, _ = download_series(key, start_date, end_date)
        (output / (key + ".csv")).write_bytes(raw)
    return load_snapshot(output)


def load_snapshot(folder):
    """Validate each original series header, frequency and precision."""
    folder = Path(folder)
    return pd.concat([read_series((folder / (key + ".csv")).read_bytes(), key)
                      for key in SERIES], axis=1).sort_index()


def complete_dates(frame):
    values = frame[list(SERIES)].astype(float)
    valid = np.isfinite(values).all(axis=1)
    valid &= (values.TAU1 > 0) & (values.TAU2 > 0)
    return frame.index[valid]


def normalize_parameters(row):
    values = [float(row[name]) for name in PARAMETERS]
    return SvenssonParameters(*[v / 100 for v in values[:4]], *values[4:])


def validate_reconstruction(row):
    years = np.arange(1, 31, dtype=float)
    keys = [f"Y{year:02d}" for year in range(1, 31)]
    observed = pd.DataFrame({
        "country": "DE", "observation_date": row.name.date().isoformat(),
        "maturity_years": years, "compounding": "annual",
        "spot_rate_decimal": [float(row[key]) / 100 for key in keys],
    })
    model = observed.copy()
    model["spot_rate_decimal"] = spot_rate(years, normalize_parameters(row))
    result = compare_spot_rates(observed, model, tolerance_bp=0)
    result["reference_series_id"] = ["BBSIS." + SERIES[key] for key in keys]
    result["reference_rounding_bp"] = 0.5
    result["parameter_rounding_bound_bp"] = parameter_rounding_bound(row, years)
    result["numerical_allowance_bp"] = 1e-9
    result["tolerance_bp"] = (result.reference_rounding_bp
                              + result.parameter_rounding_bound_bp
                              + result.numerical_allowance_bp)
    result["within_tolerance"] = result.error_bp.abs() <= result.tolerance_bp
    return result
