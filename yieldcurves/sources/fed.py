"""Read the Fed nominal CSV and reconstruct continuous zero-coupon rates."""

import csv
import argparse
from datetime import datetime, timezone
from decimal import Decimal
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
from yieldcurves.validation import compare_spot_rates

SOURCE_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
PARAMETERS = ["BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]
REFERENCES = [f"SVENY{year:02d}" for year in range(1, 31)]
MISSING = {"", "NA", "N/A", "ND", "."}


def read_fed_csv(raw):
    """Keep source tokens for precision analysis; reject unexpected formats."""
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
    """Select latest complete NSS row on/before the cutoff, without filling."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(requested_date)):
        raise ValueError("Requested date must be YYYY-MM-DD.")
    cutoff = pd.Timestamp(requested_date)
    if pd.isna(cutoff) or cutoff.tzinfo is not None:
        raise ValueError("Requested date must be a timezone-free calendar date.")
    columns = PARAMETERS + REFERENCES
    values = frame[columns].replace(dict.fromkeys(MISSING, np.nan)).astype(float)
    valid = np.isfinite(values).all(axis=1)
    valid &= (values["TAU1"] > 0) & (values["TAU2"] > 0)
    valid &= frame.Date.ge("1980-01-01") & frame.Date.le(cutoff)
    candidates = frame.loc[valid]
    if candidates.empty:
        raise ValueError("No complete post-1979 NSS date with all 30 SVENY rates.")
    return candidates.iloc[-1]


def normalize_parameters(row):
    """Convert beta percentages to decimals, leaving tau values in years."""
    values = [float(row[name]) for name in PARAMETERS]
    return SvenssonParameters(*[value / 100 for value in values[:4]], *values[4:])


def parameter_rounding_bound(row, maturity):
    """Bound spot error in bp from half a last printed parameter digit."""
    values = np.array([float(row[name]) for name in PARAMETERS])
    half_steps = np.array([
        float(Decimal(10) ** Decimal(row[name]).as_tuple().exponent) / 2
        for name in PARAMETERS
    ])
    values[:4] /= 100
    half_steps[:4] /= 100
    tau_min = values[4:] - half_steps[4:]
    if (tau_min <= 0).any():
        raise ValueError("Parameter precision interval reaches non-positive tau.")
    beta_max = np.abs(values[:4]) + half_steps[:4]
    # L(x)=integral_0^1 exp(-u*x)du; |L'|<=1/2 and |(L-exp)'|<=3/2.
    tau_error = maturity * (
        half_steps[4] * (beta_max[1] / 2 + 1.5 * beta_max[2]) / tau_min[0] ** 2
        + half_steps[5] * 1.5 * beta_max[3] / tau_min[1] ** 2
    )
    return (half_steps[:4].sum() + tau_error) * 10_000


def validate_reconstruction(row):
    """Compare all 30 spots with a precision-derived per-maturity tolerance."""
    years = np.arange(1, 31, dtype=float)
    references = np.array([float(row[name]) / 100 for name in REFERENCES])
    # The inspected export uses four decimal places in percent, suppressing zeros.
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


def download_csv(*, timeout=30, attempts=3):
    """Download with bounded transient retries; forbidden access fails immediately."""
    if not 1 <= attempts <= 3 or not 0 < timeout <= 120:
        raise ValueError("Use 1-3 attempts and a timeout in (0, 120] seconds.")
    for attempt in range(attempts):
        try:
            with urlopen(SOURCE_URL, timeout=timeout) as response:
                raw = response.read()
            read_fed_csv(raw)
            return raw
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(
                    f"Fed HTTP {exc.code}. Download the official CSV in a browser "
                    "and use --import-file with --expected-sha256."
                ) from exc
            error = exc
        except (URLError, TimeoutError) as exc:
            error = exc
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Fed download failed after {attempts} attempts: {error}")


def save_snapshot(raw, output, *, acquisition, retrieved_at_utc=None):
    """Validate before preserving raw bytes and acquisition metadata in a new folder."""
    frame = read_fed_csv(raw)
    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "source_url": SOURCE_URL,
        "source_page": "https://www.federalreserve.gov/data/nominal-yield-curve.htm",
        "retrieved_at_utc": retrieved_at_utc,
        "saved_at_utc": now,
        "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
        "acquisition": acquisition, "native_compounding": "continuous",
        "rate_unit": "percent", "tau_unit": "years", "currency": "USD",
        "universe": "off-the-run nominal Treasury coupon securities",
        "release_status": "staff research product; not a Board statistical release",
        "snapshot_rows": len(frame),
        "snapshot_last_date": frame.Date.max().date().isoformat(),
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "feds200628.csv").write_bytes(raw)
    (output / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def import_snapshot(source, expected_sha256, output):
    """Check transferred bytes; source authenticity still requires acquisition evidence."""
    raw = Path(source).read_bytes()
    if sha256(raw).hexdigest() != expected_sha256.lower():
        raise ValueError("Imported file differs from the expected SHA256.")
    return save_snapshot(raw, output, acquisition="user-supplied official CSV import")


def main():
    parser = argparse.ArgumentParser(description="Acquire a genuine Fed CSV snapshot.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true")
    mode.add_argument("--import-file", type=Path)
    parser.add_argument("--expected-sha256", help="Required checksum for local import.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.import_file and not args.expected_sha256:
        parser.error("--import-file requires --expected-sha256")
    try:
        if args.download:
            raw = download_csv()
            metadata = save_snapshot(
                raw, args.output_dir, acquisition="direct HTTPS from official CSV URL",
                retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        else:
            metadata = import_snapshot(
                args.import_file, args.expected_sha256, args.output_dir
            )
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f"Fed acquisition failed: {exc}\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
