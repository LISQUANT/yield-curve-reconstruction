"""Compare matching observations in the same rate convention."""

import numpy as np


def compare_spot_rates(observations, reconstructed, *, tolerance_bp):
    """Require complete one-to-one country/date/maturity/convention matches."""
    keys = ["country", "observation_date", "maturity_years", "compounding"]
    if not np.isfinite(tolerance_bp) or tolerance_bp < 0:
        raise ValueError("Tolerance must be finite and non-negative.")
    for frame in (observations, reconstructed):
        required = set(keys + ["spot_rate_decimal"])
        if not required.issubset(frame.columns):
            missing = sorted(required - set(frame.columns))
            raise ValueError(f"Missing curve columns: {missing}")
        if frame[keys].isna().any().any() or frame.duplicated(keys).any():
            raise ValueError("Observation keys must be complete and unique.")
        years = frame["maturity_years"]
        if not np.isfinite(years).all() or (years < 0).any():
            raise ValueError("Maturities must be finite and non-negative.")
        if not frame["compounding"].isin(["continuous", "annual"]).all():
            raise ValueError("Unsupported spot compounding convention.")
        if not np.isfinite(frame["spot_rate_decimal"]).all():
            raise ValueError("Spot rates must be finite decimal values.")
    result = observations.merge(
        reconstructed,
        on=keys,
        how="outer",
        suffixes=("_official", "_model"),
        validate="one_to_one",
        indicator=True,
    )
    if result.empty or not result["_merge"].eq("both").all():
        raise ValueError("Official and model rows do not match completely.")
    result["error_bp"] = (
        result["spot_rate_decimal_model"] - result["spot_rate_decimal_official"]
    ) * 10_000
    result["within_tolerance"] = result["error_bp"].abs() <= tolerance_bp
    return result.drop(columns="_merge")
