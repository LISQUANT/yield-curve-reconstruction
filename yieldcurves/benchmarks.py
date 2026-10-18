"""Indicative Portuguese benchmark yields, never zero-coupon rates."""

from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


def read_snapshot(folder, date):
    folder = Path(folder)
    raw = (folder / "observations.csv").read_bytes()
    meta = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    if meta.get("sha256") != sha256(raw).hexdigest():
        raise ValueError("Benchmark snapshot checksum mismatch.")
    if not meta.get("usage_permission") or not meta.get("quote_convention"):
        raise ValueError("Document permission and the benchmark quote convention.")
    frame = pd.read_csv(folder / "observations.csv")
    required = ["country", "currency", "observation_date", "maturity_years",
                "yield_percent", "source_url", "retrieved_at_utc", "quantity"]
    if (not set(required).issubset(frame) or frame.empty
            or frame[required].isna().any().any()):
        raise ValueError("Incomplete benchmark observations.")
    if (not frame.country.eq("PT").all() or not frame.currency.eq("EUR").all()
            or not frame.quantity.eq("benchmark_yield_observation").all()
            or frame.observation_date.nunique() != 1):
        raise ValueError("Require one date of Portuguese EUR benchmark yields.")
    observed = pd.to_datetime(frame.observation_date, format="%Y-%m-%d", errors="raise")
    retrieved = pd.to_datetime(frame.retrieved_at_utc, utc=True, errors="raise")
    if (retrieved.isna().any() or (retrieved.dt.tz_localize(None) < observed).any()
            or not frame.source_url.str.startswith("https://").all()):
        raise ValueError("Invalid benchmark provenance dates or URLs.")
    values = frame[["maturity_years", "yield_percent"]].to_numpy(dtype=float)
    if (not np.isfinite(values).all() or not frame.maturity_years.between(0.25, 50).all()
            or not frame.yield_percent.between(-10, 30).all()
            or frame.maturity_years.duplicated().any() or len(frame) < 2):
        raise ValueError("Invalid benchmark maturities or percent yields.")
    if meta.get("publisher") == "Banco de Portugal":
        from yieldcurves.sources.bpstat import verify_snapshot
        verify_snapshot(folder, frame, meta)
    if not frame.observation_date.eq(date).all():
        return None, meta
    return frame.sort_values("maturity_years").reset_index(drop=True), meta


def shape(years, parameters):
    """Evaluate an NS/NSS yield shape in percent, without spot-rate semantics."""
    b0, b1, b2, tau1 = parameters[:4]
    x = np.asarray(years) / tau1
    slope = -np.expm1(-x) / x
    result = b0 + b1 * slope + b2 * (slope - np.exp(-x))
    if len(parameters) == 6:
        b3, tau2 = parameters[4:]
        x = np.asarray(years) / tau2
        result += b3 * (-np.expm1(-x) / x - np.exp(-x))
    return result


def _fit(years, yields, model):
    lower, upper = [-10, -30, -30, 0.1], [30, 30, 30, 30]
    if model == "NSS":
        lower += [-30, 0.1]
        upper += [30, 30]
    fits = []
    for tau1, tau2 in [(0.5, 3), (1, 5), (2, 10), (5, 1), (10, 2)]:
        start = [float(np.clip(yields[-1], -9, 29)), -1, 1, tau1]
        if model == "NSS":
            start += [-1, tau2]
        fit = least_squares(lambda p: (shape(years, p)-yields)*100, start,
                            bounds=(lower, upper), x_scale="jac", max_nfev=1500)
        if fit.success and np.isfinite(fit.fun).all():
            fits.append(fit)
    return fits


def fit_benchmarks(frame):
    years = frame.maturity_years.to_numpy(dtype=float)
    yields = frame.yield_percent.to_numpy(dtype=float)
    grid = np.linspace(years.min(), years.max(), 281)
    diagnostics = []
    chosen = None
    for model, count in [("NS", 4), ("NSS", 6)]:
        if len(years) < count + 2:
            diagnostics.append({"model": model, "eligible": False,
                                "reason": "Need at least parameter count plus two observations."})
            continue
        fits = _fit(years, yields, model)
        if not fits:
            diagnostics.append({"model": model, "eligible": False, "reason": "No convergence."})
            continue
        best = min(fits, key=lambda result: np.sum(result.fun**2))
        singular = np.linalg.svd(best.jac, compute_uv=False)
        condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else None
        near = [fit for fit in fits if np.sqrt(np.mean(fit.fun**2))
                <= np.sqrt(np.mean(best.fun**2)) + 0.1]
        start_spread = float(np.ptp([shape(grid, fit.x) for fit in near], axis=0).max()*100)
        leave_out = []
        for i in range(1, len(years)-1):
            keep = np.arange(len(years)) != i
            alternatives = _fit(years[keep], yields[keep], model)
            if not alternatives:
                leave_out.append(None)
                continue
            fit = min(alternatives, key=lambda result: np.sum(result.fun**2))
            leave_out.append(float(np.max(np.abs(shape(grid, fit.x)-shape(grid, best.x)))*100))
        sensitivity = max(leave_out) if all(x is not None for x in leave_out) else None
        eligible = (condition is not None and condition < 1e8
                    and not np.any(best.active_mask) and start_spread <= 2
                    and sensitivity is not None and sensitivity <= 5
                    and np.max(np.abs(best.fun)) <= 5)
        diagnostics.append({"model": model, "eligible": bool(eligible),
                            "parameters_percent_years": best.x.tolist(),
                            "rmse_bp": float(np.sqrt(np.mean(best.fun**2))),
                            "max_error_bp": float(np.max(np.abs(best.fun))),
                            "jacobian_condition": condition, "start_spread_bp": start_spread,
                            "interior_leave_one_out_max_change_bp": sensitivity,
                            "starts": [{"parameters": f.x.tolist(),
                                        "rmse_bp": float(np.sqrt(np.mean(f.fun**2)))} for f in fits]})
        if eligible and chosen is None:
            chosen = best
            selected = model
    if chosen is None:
        selected = "connected_observations"
        fitted = np.interp(grid, years, yields)
        residual = np.zeros(len(years))
    else:
        fitted = shape(grid, chosen.x)
        residual = (shape(years, chosen.x)-yields)*100
    curve = pd.DataFrame({"country": "PT", "currency": "EUR",
                          "observation_date": frame.observation_date.iloc[0],
                          "maturity_years": grid, "yield_percent": fitted,
                          "quantity": "indicative_benchmark_fit", "method": selected})
    residuals = frame.copy()
    residuals["display_minus_observed_bp"] = residual
    summary = {"method": selected, "observation_count": len(years),
               "observation_date": frame.observation_date.iloc[0],
               "support_years": [float(years.min()), float(years.max())],
               "diagnostic_fits": diagnostics,
               "interpretation": "Benchmark yield interpolation; not a zero-coupon curve.",
               "display_rmse_bp": float(np.sqrt(np.mean(residual**2))),
               "residual_note": "Connected-point zero residuals are an identity, not validation."
                                if chosen is None else "In-sample smoothing errors, not official validation."}
    return curve, residuals, summary


def export_snapshot(folder, output, date):
    frame, meta = read_snapshot(folder, date)
    if frame is None:
        return {"available": False, "reason": "No benchmark observations for the selected date."}
    curve, residuals, summary = fit_benchmarks(frame)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    curve.to_csv(output / "indicative_curve.csv", index=False)
    residuals.to_csv(output / "observations_and_residuals.csv", index=False)
    for name in ["observations.csv", "provenance.json", *meta.get("source_files", {})]:
        shutil.copyfile(Path(folder) / name, output / name)
    summary.update({"available": True, "usage_permission": meta["usage_permission"],
                    "retrieved_at_utc": sorted(set(frame.retrieved_at_utc)),
                    "source_urls": sorted(set(frame.source_url))})
    (output / "diagnostics.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    from yieldcurves.plots import plot_benchmarks
    plot_benchmarks(frame, curve, output / "benchmark_yields")
    return summary
