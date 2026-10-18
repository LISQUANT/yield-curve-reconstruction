"""Daily Portuguese Treasury benchmark yields from Banco de Portugal."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    output.mkdir(parents=True, exist_ok=False)
    observations, files = [], {}
    for maturity, series_id in SERIES.items():
        url = API + "?" + urlencode({"lang": "EN", "series_ids": series_id, "obs_since": date})
        request = Request(url, headers={"User-Agent": "LIS-Yield-Curve-Research/1.0",
                                        "Accept": "application/json"})
        with urlopen(request, timeout=30) as response:
            raw = response.read()
        name = f"{series_id}.json"
        (output / name).write_bytes(raw)
        retrieved = datetime.now(timezone.utc).isoformat()
        files[name] = {"source_url": url, "retrieved_at_utc": retrieved,
                       "sha256": sha256(raw).hexdigest(), "series_id": series_id}
        row = read_response(raw, series_id, maturity, date)
        observations.append({"country": "PT", "currency": "EUR", "observation_date": date,
                             "maturity_years": maturity, **row, "source_url": url,
                             "retrieved_at_utc": retrieved, "quantity": "benchmark_yield_observation"})
    pd.DataFrame(observations).to_csv(output / "observations.csv", index=False)
    metadata = {"publisher": "Banco de Portugal", "source": "LSEG",
                "source_files": files, "observation_date": date,
                "sha256": sha256((output / "observations.csv").read_bytes()).hexdigest(),
                "quote_convention": "Daily average fixed-rate Treasury bond yields; not zero-coupon rates.",
                "usage_permission": "BPstat legal notice permits use, accurate redistribution with Banco de Portugal attribution, and explicit disclosure of modifications.",
                "rights_url": RIGHTS, "rights_review_date": "2026-10-18",
                "transformation": "Selected exact date from six original JSON-stat replies; values unchanged.",
                "acquisition": "Direct official HTTPS API; original response bytes retained."}
    (output / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def verify_snapshot(folder, frame, metadata):
    files = metadata.get("source_files", {})
    if set(files) != {f"{sid}.json" for sid in SERIES.values()} or len(frame) != len(SERIES):
        raise ValueError("BPstat snapshot must contain all six original replies.")
    for maturity, sid in SERIES.items():
        entry = files[f"{sid}.json"]
        raw = (Path(folder) / f"{sid}.json").read_bytes()
        if entry["sha256"] != sha256(raw).hexdigest() or not entry["source_url"].startswith(API + "?"):
            raise ValueError("Invalid BPstat original-response provenance.")
        rows = frame.loc[frame.maturity_years == maturity]
        if len(rows) != 1:
            raise ValueError("Missing BPstat maturity.")
        row = rows.iloc[0]
        original = read_response(raw, sid, maturity, row.observation_date)
        if (row.yield_percent != original["yield_percent"] or row.series_id != sid
                or row.observation_status != original["observation_status"]
                or row.source_url != entry["source_url"]
                or row.retrieved_at_utc != entry["retrieved_at_utc"]):
            raise ValueError("BPstat transcription differs from the original reply.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        download_snapshot(args.output_dir, args.date)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"BPstat acquisition failed: {exc}. No complete manifest was published; retain original replies for review.\n")


if __name__ == "__main__":
    main()
