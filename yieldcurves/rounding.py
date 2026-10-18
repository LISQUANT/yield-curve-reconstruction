"""Descriptive rounding checks, independent of the validation allowance."""

from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from yieldcurves.sources import bundesbank


def german_history(frame):
    results = []
    for date in bundesbank.complete_dates(frame):
        results.append(bundesbank.validate_reconstruction(frame.loc[date]))
    if not results:
        raise ValueError("No complete German dates for the rounding check.")
    result = pd.concat(results, ignore_index=True)
    values = result.spot_rate_decimal_model * 100
    direct, double = [], []
    for value in values:
        number = Decimal(str(value))
        direct.append(float(number.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)))
        intermediate = number.quantize(Decimal(".001"), rounding=ROUND_HALF_UP)
        double.append(float(intermediate.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)))
    result["nearest_2dp_percent"] = direct
    result["via_3dp_then_2dp_percent"] = double
    published = result.spot_rate_decimal_official * 100
    for name, values in [("direct_match", direct), ("double_match", double)]:
        result[name] = np.isclose(values, published, atol=1e-10, rtol=0)
    failures = result.loc[~result.within_tolerance]
    summary = {
        "dates": int(result.observation_date.nunique()), "observations": len(result),
        "first_date": result.observation_date.min(), "last_date": result.observation_date.max(),
        "direct_matches": int(result.direct_match.sum()),
        "double_matches": int(result.double_match.sum()),
        "double_unexplained": int((~result.double_match).sum()),
        "strict_failures": len(failures), "dates_with_strict_failures": int(failures.observation_date.nunique()),
        "interpretation": "Double rounding is an empirical hypothesis, not a confirmed Bundesbank convention. Validation tolerances are unchanged.",
    }
    return result, summary
