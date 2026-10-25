"""Synthetic parser fixtures; these tests are not official-source evidence."""

import csv
from io import StringIO

import numpy as np
import pytest

from yieldcurves.sources.fed import (
    PARAMETERS, REFERENCES, normalize_parameters, parameter_rounding_bound,
    read_fed_csv, select_complete_date, validate_reconstruction,
)


def synthetic_csv(rows=None):
    columns = ["Date"] + PARAMETERS + REFERENCES
    row = ["2026-10-02", "3.00000000000000", "0.00000000000000",
           "0.00000000000000", "0.00000000000000", "1.80000000000000",
           "7.00000000000000"] + ["3.0000"] * 30
    buffer = StringIO()
    buffer.write("Synthetic fixture, not market data\n")
    buffer.write("Zero-coupon yield,Continuously Compounded,SVENYXX\n\n")
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows if rows is not None else [row])
    return buffer.getvalue().encode()


def test_flat_synthetic_reference_and_units():
    row = select_complete_date(read_fed_csv(synthetic_csv()), "2026-10-12")
    p = normalize_parameters(row)
    assert p.beta0 == 0.03 and p.tau1 == 1.8 and p.tau2 == 7
    result = validate_reconstruction(row)
    assert len(result) == 30 and result.within_tolerance.all()
    np.testing.assert_allclose(result.error_bp, 0)


@pytest.mark.parametrize("bad", [b"<html>Access denied</html>", b"",
    synthetic_csv().replace(b"Continuously Compounded", b"Annual"),
    synthetic_csv().replace(b"SVENY30", b"SVENPY30"),
    synthetic_csv().replace(b"2026-10-02", b"02-10-2026"),
    synthetic_csv().replace(b"3.0000,", b"oops,", 1)])
def test_reject_bad_source(bad):
    with pytest.raises(ValueError):
        read_fed_csv(bad)


@pytest.mark.parametrize("column,missing", [("TAU2", "-999.99"),
                                          ("BETA1", "NA"), ("SVENY30", "NA")])
def test_skip_incomplete_latest_without_filling(column, missing):
    frame = read_fed_csv(synthetic_csv())
    old = ["2026-10-01"] + frame.iloc[0][PARAMETERS + REFERENCES].tolist()
    new = ["2026-10-02"] + frame.iloc[0][PARAMETERS + REFERENCES].tolist()
    new[(["Date"] + PARAMETERS + REFERENCES).index(column)] = missing
    selected = select_complete_date(read_fed_csv(synthetic_csv([old, new])), "2026-10-12")
    assert selected.Date.date().isoformat() == "2026-10-01"


def test_duplicate_dates_rejected():
    raw = synthetic_csv()
    with pytest.raises(ValueError, match="Duplicate observation"):
        read_fed_csv(raw + raw.splitlines()[-1] + b"\n")


def test_no_complete_date_and_pre_1980_rejected():
    frame = read_fed_csv(synthetic_csv())
    with pytest.raises(ValueError, match="No complete"):
        select_complete_date(frame, "2026-10-01")
    old = read_fed_csv(synthetic_csv().replace(b"2026-10-02", b"1979-12-31"))
    with pytest.raises(ValueError, match="No complete"):
        select_complete_date(old, "2026-10-12")


def test_wrong_reference_is_a_failure_not_a_wider_tolerance():
    row = select_complete_date(read_fed_csv(synthetic_csv()), "2026-10-12").copy()
    row["SVENY01"] = "3.0100"
    result = validate_reconstruction(row)
    assert not result.within_tolerance.iloc[0]
    assert result.error_bp.iloc[0] == pytest.approx(-1)
    assert result.tolerance_bp.iloc[0] < 0.005001


def test_parameter_rounding_bound_covers_perturbation():
    from yieldcurves.svensson import spot_rate

    row = select_complete_date(read_fed_csv(synthetic_csv()), "2026-10-12").copy()
    row["BETA1"], row["BETA2"], row["BETA3"] = "-1.500000", "1.200000", "-0.600000"
    row["TAU1"], row["TAU2"] = "1.800000", "7.000000"
    years = np.arange(1, 31)
    base = spot_rate(years, normalize_parameters(row))
    bound = parameter_rounding_bound(row, years)
    changed = row.copy()
    for name in ["BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]:
        changed[name] = str(float(row[name]) + 0.0000005)
    errors = np.abs(spot_rate(years, normalize_parameters(changed)) - base) * 10_000
    assert (errors <= bound).all()
