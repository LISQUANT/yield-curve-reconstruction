"""Download sovereign data and export the latest common complete curve date."""

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re

import pandas as pd
import requests

from yieldcurves.sources import bundesbank, fed, bportugal
from yieldcurves.reconstruction import reconstruct, reconstruct_germany, error_summary
from yieldcurves.plots import plot_research

ROOT = Path(__file__).resolve().parents[1]


def common_date(fed_frame, german_frame, cutoff):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cutoff)):
        raise ValueError("Use a cutoff date in YYYY-MM-DD format.")
    cutoff = pd.Timestamp(cutoff)
    dates = fed.complete_dates(fed_frame)
    if german_frame is not None:
        dates = dates.intersection(bundesbank.complete_dates(german_frame))
    dates = dates[dates <= cutoff]
    if dates.empty:
        raise ValueError("No complete common date on or before the cutoff.")
    return dates.max().date().isoformat()


def acquire(data, cutoff, *, offline=False, fed_file=None, germany_dir=None):
    """Download directly unless the caller explicitly supplies saved inputs."""
    data = Path(data)
    us_file = Path(fed_file) if fed_file else data / "US/feds200628.csv"
    if not offline and fed_file is None:
        raw = fed.download_csv()
        us_file.parent.mkdir(parents=True, exist_ok=True)
        us_file.write_bytes(raw)
    us = fed.read_fed_csv(us_file.read_bytes())
    latest = fed.select_complete_date(us, cutoff).Date.date()
    de_folder = Path(germany_dir) if germany_dir else data / "DE"
    if not offline and germany_dir is None:
        bundesbank.download_snapshot(de_folder, (latest-timedelta(days=7)).isoformat(), latest.isoformat())
    de = bundesbank.load_snapshot(de_folder)
    return us_file, us, de


def run(data_dir, output, cutoff, *, offline=False, portugal_dir=None,
        portugal_benchmarks=None, fed_file=None, germany_dir=None):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cutoff)):
        raise ValueError("Use a cutoff date in YYYY-MM-DD format.")
    date.fromisoformat(cutoff)
    output = Path(output)
    if output.exists():
        raise FileExistsError("Output directory already exists; choose a new run directory.")
    us_file, us, de = acquire(data_dir, cutoff, offline=offline, fed_file=fed_file,
                              germany_dir=germany_dir)
    selected = common_date(us, de, cutoff)
    output.mkdir(parents=True)
    reconstruct(us_file, selected, output / "US")
    reconstruct_germany(de, selected, output / "DE")
    from yieldcurves.rounding import german_history
    rounding_rows, rounding_summary = german_history(de)
    rounding_rows.to_csv(output / "DE/rounding_history.csv", index=False)
    (output / "DE/rounding_history.json").write_text(json.dumps(rounding_summary, indent=2))
    portugal_result = None
    if portugal_dir is not None:
        from yieldcurves.portugal import estimate
        portugal_result = estimate(portugal_dir, output / "PT", selected)
    benchmark_folder = Path(portugal_benchmarks) if portugal_benchmarks else Path(data_dir) / "PT"
    messages = []
    benchmark_result = {"available": False, "reason": "No same-date Portuguese benchmark data supplied."}
    if not offline and portugal_benchmarks is None:
        try:
            bportugal.download_snapshot(benchmark_folder, selected)
        except (OSError, ValueError, requests.RequestException) as exc:
            messages.append(f"Banco de Portugal download failed: {exc}")
            benchmark_result["reason"] = messages[-1]
    if not messages and (benchmark_folder / "observations.csv").exists():
        from yieldcurves.benchmarks import export_snapshot
        benchmark_result = export_snapshot(benchmark_folder, output / "PT_benchmarks", selected)
    curves = pd.concat([pd.read_csv(output / c / "curve.csv") for c in ["US", "DE"]], ignore_index=True)
    validations = {c: pd.read_csv(output / c / "validation.csv") for c in ["US", "DE"]}
    curves.to_csv(output / "curves.csv", index=False)
    pd.concat(validations.values(), ignore_index=True).to_csv(output / "validation.csv", index=False)
    curves.loc[curves.maturity_years.isin([1, 2, 5, 10, 20, 30])].to_csv(
        output / "selected_maturities.csv", index=False)
    figures = output / "figures"
    figures.mkdir()
    plot_research(curves, validations, figures)
    results = {c: error_summary(v) for c, v in validations.items()}
    pd.DataFrame.from_dict(results, orient="index").rename_axis("country").to_csv(output / "summary.csv")
    return {"requested_date": cutoff, "observation_date": selected, "validation": results,
            "validation_passed": all(r["validation_passed"] for r in results.values()),
            "german_rounding_history": rounding_summary, "portugal_calibration": portugal_result,
            "portugal_benchmarks": benchmark_result, "acquisition_messages": messages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat(), help="Latest permitted observation date.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fed-file", type=Path, help="Official CSV downloaded manually; no manifest required.")
    parser.add_argument("--germany-dir", type=Path, help="Folder of original Bundesbank series CSVs.")
    parser.add_argument("--portugal-dir", type=Path, help="Bond prices and contractual cash flows.")
    parser.add_argument("--portugal-benchmarks", type=Path, help="Folder containing benchmark observations.csv.")
    parser.add_argument("--offline", action="store_true", help="Use supplied files without downloads.")
    args = parser.parse_args()
    output = args.output_dir or ROOT / "outputs" / datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    try:
        result = run(args.data_dir, output, args.date, offline=args.offline,
                     portugal_dir=args.portugal_dir, portugal_benchmarks=args.portugal_benchmarks,
                     fed_file=args.fed_file, germany_dir=args.germany_dir)
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Reconstruction failed: {exc}\n")
    print(f"Observation date: {result['observation_date']}\nResults: {output}")
    for country, stats in result["validation"].items():
        print(f"{country}: {stats['passed_count']}/{stats['reference_count']} within rounding tolerance; "
              f"maximum error {stats['max_absolute_error_bp']:.6f} bp")
    print("PT benchmarks: " + (result["portugal_benchmarks"].get("method") or result["portugal_benchmarks"]["reason"]))
    if result["acquisition_messages"]:
        parser.exit(1, "\n".join(result["acquisition_messages"]) + "\nUS/German outputs were retained.\n")
    if not result["validation_passed"]:
        parser.exit(2, "Outputs generated with validation exceptions; see validation.csv.\n")


if __name__ == "__main__":
    main()
