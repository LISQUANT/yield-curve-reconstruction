"""A synthetic double-rounding case must retain strict validation failures."""

import pandas as pd

from yieldcurves.rounding import german_history
from yieldcurves.sources.bundesbank import PARAMETERS


def test_double_rounding_does_not_relax_validation():
    values = dict(zip(PARAMETERS, ["3.00472", "0.00000", "0.00000", "0.00000", "1.00000", "1.00000"]))
    values.update({f"Y{year:02d}": "3.01" for year in range(1, 31)})
    frame = pd.DataFrame([values], index=pd.to_datetime(["2026-10-02"]))
    rows, stats = german_history(frame)
    assert stats["dates"] == 1 and stats["observations"] == 30
    assert stats["direct_matches"] == 0 and stats["double_matches"] == 30
    assert not rows.within_tolerance.iloc[0]
    assert rows.nearest_2dp_percent.iloc[0] == 3.00
    assert rows.via_3dp_then_2dp_percent.iloc[0] == 3.01
