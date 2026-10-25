"""Daily Portuguese Treasury benchmark yields from Banco de Portugal."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import requests

import numpy as np
import pandas as pd

SERIES = {2: 12099454, 3: 12099455, 4: 12099456, 5: 12099457, 7: 12099458, 10: 12099459}
API = "https://bpstat.bportugal.pt/data/v1/domains/26/datasets/690b7b36fd36c0dbe249c48cbbc39524/"
RIGHTS = "https://bpstat.bportugal.pt/avisos-legais"


def read_response(raw, series_id, maturity, date):
    data = json.loads(raw)
    if (data.get("class") != "dataset" or data.get("version") != "2.0"
            or data.get("source") != "Bank of Portugal"):
        raise ValueError("Unexpected BPstat dataset.")
    series = data.get("extension", {}).get("series", [])
    if len(series) != 1 or series[0].get("id") != series_id:
        raise ValueError("Incorrect BPstat series identity.")
    expected = {"Source": "LSEG", "Periodicity": "Daily", "Residual maturity": f"{maturity} years",
                "Unit of measure": "Percentage", "Reference territory": "Portugal",
                "Metrics": "Average", "Indicators": "Yield on TB (Treasury Bonds)"}
    dimensions = data.get("dimension", {})
    labels = {d["label"]: list(d["category"].get("label", {}).values()) for d in dimensions.values()}
    if any(labels.get(name) != [value] for name, value in expected.items()):
        raise ValueError("Unexpected BPstat units, maturity, frequency or source.")
    ids, sizes = data.get("id", []), data.get("size", [])
    if (len(ids) != len(sizes) or not ids or ids[-1] != "reference_date"
            or any(size != 1 for size in sizes[:-1])):
        raise ValueError("Expected one series with dates on the final JSON-stat axis.")
    dates = dimensions["reference_date"]["category"]["index"]
    if isinstance(dates, dict):
        dates = sorted(dates, key=dates.get)
    if len(dates) != sizes[-1] or len(set(dates)) != len(dates) or date not in dates:
        raise ValueError("Missing or inconsistent BPstat dates.")
    values, status = data.get("value"), data.get("status")
    if not isinstance(values, list) or not isinstance(status, list) or len(values) != len(dates) or len(status) != len(dates):
        raise ValueError("Incomplete BPstat observations or status.")
    position = dates.index(date)
    value = values[position]
    if value is None or not isinstance(value, (float, int)) or not np.isfinite(value) or status[position] != "F":
        raise ValueError("Require a finite BPstat observation with F status.")
    return {"yield_percent": value, "observation_status": status[position],
            "series_id": series_id, "source_label": "LSEG via Banco de Portugal",
            "published_label": series[0]["label"]}


def download_snapshot(output, date):
    date = pd.Timestamp(date).date().isoformat()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    observations = []
    for maturity, series_id in SERIES.items():
        response = requests.get(API, params={"lang": "EN", "series_ids": series_id,
                                            "obs_since": date}, timeout=30)
        response.raise_for_status()
        row = read_response(response.content, series_id, maturity, date)
        (output / f"{series_id}.json").write_bytes(response.content)
        observations.append({"country": "PT", "currency": "EUR", "observation_date": date,
                             "maturity_years": maturity, **row, "source_url": response.url,
                             "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                             "quantity": "benchmark_yield_observation"})
    frame = pd.DataFrame(observations)
    frame.to_csv(output / "observations.csv", index=False)
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        download_snapshot(args.output_dir, args.date)
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Banco de Portugal acquisition failed: {exc}\n")


if __name__ == "__main__":
    main()
