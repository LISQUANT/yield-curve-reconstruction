"""Daily German federal-security spot rates and Svensson parameters."""

import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

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


def download_series(key, start_date):
    pd.to_datetime(start_date, format="%Y-%m-%d", errors="raise")
    url = API + SERIES[key] + f"?format=csv&lang=en&startPeriod={start_date}"
    for attempt in range(3):
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read()
            read_series(raw, key)
            return raw, url
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"Bundesbank HTTP {exc.code}: {key}") from exc
            error = exc
        except (URLError, TimeoutError) as exc:
            error = exc
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Bundesbank download failed for {key}: {error}")


def download_snapshot(output, start_date):
    """Save all 36 series; a manifest is written only after validation."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    metadata = {"source_page": SOURCE_PAGE, "native_compounding": "annual",
                "rate_unit": "percent", "tau_unit": "years", "currency": "EUR",
                "acquisition": "direct HTTPS from official Bundesbank API",
                "files": {}}
    for key in SERIES:
        raw, url = download_series(key, start_date)
        filename = key + ".csv"
        (output / filename).write_bytes(raw)
        metadata["files"][filename] = {
            "series_id": "BBSIS." + SERIES[key], "source_url": url,
            "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    (output / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return load_snapshot(output)


def load_snapshot(folder):
    folder = Path(folder)
    meta = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    if (meta.get("native_compounding"), meta.get("rate_unit"),
            meta.get("tau_unit")) != ("annual", "percent", "years"):
        raise ValueError("Unexpected Bundesbank units or compounding.")
    if set(meta["files"]) != {key + ".csv" for key in SERIES}:
        raise ValueError("Snapshot must contain six parameters and 30 spot series.")
    columns = []
    for key, series in SERIES.items():
        entry = meta["files"][key + ".csv"]
        raw = (folder / (key + ".csv")).read_bytes()
        if entry["sha256"] != sha256(raw).hexdigest():
            raise ValueError(f"Bundesbank checksum mismatch: {key}")
        if (entry["series_id"] != "BBSIS." + series
                or not entry["source_url"].startswith(API + series + "?")):
            raise ValueError(f"Unexpected Bundesbank provenance: {key}")
        columns.append(read_series(raw, key))
    frame = pd.concat(columns, axis=1).sort_index()
    return frame, meta


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
