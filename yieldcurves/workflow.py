"""Reconstruct saved sovereign curves on the latest common complete date."""

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re

import matplotlib
import numpy as np
import pandas as pd

from yieldcurves.sources import bundesbank, fed
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


def acquire(data, cutoff, refresh=False, offline=False):
    """Use pinned local snapshots; downloads never overwrite source bytes."""
    data = Path(data)
    config = data / "snapshots.json"
    paths = json.loads(config.read_text()) if config.exists() else {}
    messages = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    for country in ["US", "DE"]:
        if country in paths and not refresh:
            continue
        if offline:
            if country not in paths:
                messages.append(f"{country}: no configured snapshot; offline mode.")
            continue
        destination = data / "raw" / country / stamp
        try:
            if country == "US":
                raw = fed.download_csv()
                fed.save_snapshot(raw, destination, acquisition="direct official HTTPS",
                                  retrieved_at_utc=datetime.now(timezone.utc).isoformat())
            else:
                start = (date.fromisoformat(cutoff) - timedelta(days=366)).isoformat()
                bundesbank.download_snapshot(destination, start)
            paths[country] = destination.relative_to(data).as_posix()
        except (OSError, RuntimeError) as exc:
            messages.append(f"{country}: {exc}; retained saved snapshot if configured.")
    if "US" not in paths:
        raise ValueError("No Fed snapshot. Import its official CSV and configure data/snapshots.json.")
    if not offline:
        data.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(paths, indent=2) + "\n")
    return {country: data / folder for country, folder in paths.items()}, messages


def run(data_dir, output, cutoff, *, refresh=False, offline=False, portugal_dir=None,
        portugal_benchmarks=None):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cutoff)):
        raise ValueError("Use a cutoff date in YYYY-MM-DD format.")
    date.fromisoformat(cutoff)
    if refresh and offline:
        raise ValueError("Choose either refresh or offline mode.")
    output = Path(output)
    if output.exists():
        raise FileExistsError("Output directory already exists; choose a new run directory.")
    paths, messages = acquire(data_dir, cutoff, refresh, offline)
    us_file = paths["US"] / "feds200628.csv"
    us = fed.read_fed_csv(us_file.read_bytes())
    de, de_meta = bundesbank.load_snapshot(paths["DE"]) if "DE" in paths else (None, None)
    selected = common_date(us, de, cutoff)
    output.mkdir(parents=True)
    summaries = {"US": reconstruct(us_file, paths["US"] / "provenance.json",
                                    selected, output / "US")}
    if de is not None:
        summaries["DE"] = reconstruct_germany(de, de_meta, selected, output / "DE")
    rounding_summary = None
    if de is not None:
        from yieldcurves.rounding import german_history
        rounding_rows, rounding_summary = german_history(de)
        rounding_rows.to_csv(output / "DE/rounding_history.csv", index=False)
        (output / "DE/rounding_history.json").write_text(json.dumps(rounding_summary, indent=2))
    portugal_result = None
    if portugal_dir is not None:
        from yieldcurves.portugal import estimate
        portugal_result = estimate(portugal_dir, output / "PT", selected)
    benchmark_result = {"available": False, "reason": "No verified, permitted benchmark snapshot configured."}
    benchmark_folder = portugal_benchmarks or paths.get("PT_benchmarks")
    if benchmark_folder is not None:
        from yieldcurves.benchmarks import export_snapshot
        benchmark_result = export_snapshot(benchmark_folder, output / "PT_benchmarks", selected)
    curves = pd.concat([pd.read_csv(output / c / "curve.csv") for c in summaries],
                       ignore_index=True)
    validations = {c: pd.read_csv(output / c / "validation.csv") for c in summaries}
    curves.to_csv(output / "curves.csv", index=False)
    pd.concat(validations.values(), ignore_index=True).to_csv(
        output / "validation.csv", index=False)
    curves.loc[curves.maturity_years.isin([1, 2, 5, 10, 20, 30])].to_csv(
        output / "selected_maturities.csv", index=False)
    figures = output / "figures"
    figures.mkdir()
    plot_research(curves, validations, figures)
    results = {c: error_summary(v) for c, v in validations.items()}
    summary = {
        "requested_date": cutoff, "observation_date": selected,
        "date_policy": "latest common complete date, never selected for fit quality",
        "source_last_dates": {"US": us.Date.max().date().isoformat(),
                              "DE": de.index.max().date().isoformat() if de is not None else None},
        "country_status": {"US": "reconstructed", "DE": "reconstructed" if de is not None else "unavailable",
                           "PT": "not estimated: no verified same-date bond-price dataset"},
        "validation": results,
        "german_rounding_history": rounding_summary,
        "portugal_calibration": portugal_result,
        "portugal_benchmarks": benchmark_result,
        "validation_passed": all(r["validation_passed"] for r in results.values()),
        "acquisition_messages": messages,
        "comparison_note": "USD and EUR curves; the difference is not a sovereign credit spread.",
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "pandas": pd.__version__, "matplotlib": matplotlib.__version__,
                     "reportlab": version("reportlab"), "svglib": version("svglib"),
                     "scipy": version("scipy")},
    }
    if portugal_result is not None:
        summary["country_status"]["PT"] = "estimated from imported bond prices; not official spot validation"
    elif benchmark_result["available"]:
        summary["country_status"]["PT"] = "indicative benchmark yields only; no zero-coupon estimation"
    from yieldcurves.report import write_report
    write_report(output, summary, curves, validations)
    code_files = sorted((ROOT / "yieldcurves").rglob("*.py")) + [
        ROOT / "scripts/run_yield_curves.py", ROOT / "make_report.py", ROOT / "pyproject.toml"]
    summary["code_sha256"] = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
                              for p in code_files}
    summary["output_sha256"] = {p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest()
                                for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat(), help="Latest permitted observation date.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--portugal-dir", type=Path, help="Verified bonds, cash flows and provenance folder.")
    parser.add_argument("--portugal-benchmarks", type=Path,
                        help="Permitted benchmark-yield snapshot; never used for discounting.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="Attempt new official downloads.")
    mode.add_argument("--offline", action="store_true", help="Forbid downloads.")
    args = parser.parse_args()
    output = args.output_dir or ROOT / "outputs" / datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    try:
        result = run(args.data_dir, output, args.date, refresh=args.refresh, offline=args.offline,
                     portugal_dir=args.portugal_dir, portugal_benchmarks=args.portugal_benchmarks)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Reconstruction failed: {exc}\n")
    print(f"Observation date: {result['observation_date']}\nResults: {output}")
    print("PT benchmarks: " + (result["portugal_benchmarks"].get("method")
                               or result["portugal_benchmarks"]["reason"]))
    for country, stats in result["validation"].items():
        print(f"{country}: {stats['passed_count']}/{stats['reference_count']} within rounding tolerance; "
              f"maximum error {stats['max_absolute_error_bp']:.6f} bp")
    if not result["validation_passed"]:
        parser.exit(2, "Report generated with validation exceptions; see validation.csv.\n")


if __name__ == "__main__":
    main()
