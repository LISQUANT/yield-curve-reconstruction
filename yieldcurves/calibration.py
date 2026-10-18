"""Fit continuously compounded NSS rates to bond dirty prices per 100."""

from dataclasses import asdict

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from yieldcurves.svensson import SvenssonParameters, discount_factor


def bond_prices(parameters, times, cashflows):
    return cashflows @ discount_factor(times, parameters, compounding="continuous")


def fit_prices(times, cashflows, prices):
    """Use equal price weights and fixed multiple starts; report identification."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    prices = np.asarray(prices, dtype=float)
    if (times.ndim != 1 or prices.ndim != 1 or len(prices) < 7
            or cashflows.shape != (len(prices), len(times))):
        raise ValueError("Supply at least seven bonds and a matching cash-flow matrix.")
    if (not all(np.isfinite(x).all() for x in [times, cashflows, prices])
            or (times <= 0).any() or (np.diff(times) <= 0).any()
            or (prices <= 0).any() or (cashflows < 0).any()
            or (cashflows.sum(axis=1) <= 0).any()):
        raise ValueError("Invalid prices, payment times or cash flows.")
    maturities = np.max(np.where(cashflows > 0, times, 0), axis=1)
    if (len(np.unique(maturities)) < 7 or maturities.min() > 3
            or maturities.max() < 10):
        raise ValueError("Need seven distinct maturities covering <=3Y and >=10Y.")

    lower = [-0.05, -0.30, -0.30, -0.30, 0.05, 0.05]
    upper = [0.20, 0.30, 0.30, 0.30, 30.0, 30.0]

    def residual(values):
        return bond_prices(SvenssonParameters(*values), times, cashflows) - prices

    fits = []
    records = []
    for tau1, tau2 in [(0.5, 3), (1, 5), (2, 10), (5, 1), (10, 2), (3, 15)]:
        fit = least_squares(residual, [0.04, -0.02, 0.01, -0.01, tau1, tau2],
                            bounds=(lower, upper), x_scale="jac", max_nfev=3000,
                            ftol=1e-11, xtol=1e-11, gtol=1e-11)
        fits.append(fit)
        records.append({"tau1_start": tau1, "tau2_start": tau2,
                        "converged": bool(fit.success), "evaluations": fit.nfev,
                        "price_rmse": float(np.sqrt(np.mean(fit.fun**2))),
                        **asdict(SvenssonParameters(*fit.x))})
    converged = [fit for fit in fits if fit.success and np.isfinite(fit.fun).all()]
    if not converged:
        raise RuntimeError("No calibration start converged; no curve exported.")
    best = min(converged, key=lambda fit: np.sum(fit.fun**2))
    singular = np.linalg.svd(best.jac, compute_uv=False)
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else None
    warnings = []
    if condition is None or condition > 1e8:
        warnings.append("Weak parameter identification: Jacobian condition exceeds 1e8.")
    if np.any(best.active_mask):
        warnings.append("At least one fitted parameter is on a bound.")
    diagnostics = {
        "objective": "equal-weight squared dirty-price errors per 100 face value",
        "price_rmse": float(np.sqrt(np.mean(best.fun**2))),
        "max_absolute_price_error": float(np.max(np.abs(best.fun))),
        "jacobian_rank": int(np.linalg.matrix_rank(best.jac)),
        "jacobian_condition": condition, "warnings": warnings,
        "lower_bounds": lower, "upper_bounds": upper,
        "maturity_range_years": [float(maturities.min()), float(maturities.max())],
        "interpretation": "In-sample price fit; not independent zero-rate validation.",
    }
    return SvenssonParameters(*best.x), diagnostics, pd.DataFrame(records)
