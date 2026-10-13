import pandas as pd
import pytest

from yieldcurves.validation import compare_spot_rates


@pytest.fixture
def observations():
    return pd.DataFrame(
        {
            "country": ["DE"],
            "observation_date": ["2020-01-02"],
            "maturity_years": [10.0],
            "compounding": ["annual"],
            "spot_rate_decimal": [0.03],
        }
    )


def test_error_in_basis_points(observations):
    model = observations.copy()
    model["spot_rate_decimal"] = 0.030025
    result = compare_spot_rates(observations, model, tolerance_bp=0.3)
    assert result["error_bp"].iloc[0] == pytest.approx(0.25)
    assert result["within_tolerance"].iloc[0]


@pytest.mark.parametrize(
    "column,value",
    [
        ("compounding", "continuous"),
        ("observation_date", "2020-01-03"),
        ("country", "US"),
        ("maturity_years", 5.0),
    ],
)
def test_unmatched_observations_fail(observations, column, value):
    model = observations.copy()
    model[column] = value
    with pytest.raises(ValueError):
        compare_spot_rates(observations, model, tolerance_bp=0.1)


def test_duplicate_keys_fail(observations):
    duplicates = pd.concat([observations, observations])
    with pytest.raises(ValueError):
        compare_spot_rates(duplicates, observations, tolerance_bp=0.1)


def test_error_exceeding_tolerance_is_reported(observations):
    model = observations.copy()
    model["spot_rate_decimal"] = 0.0301
    result = compare_spot_rates(observations, model, tolerance_bp=0.2)
    assert not result["within_tolerance"].iloc[0]


def test_missing_column_is_reported(observations):
    with pytest.raises(ValueError, match="Missing curve columns"):
        compare_spot_rates(
            observations.drop(columns="compounding"), observations, tolerance_bp=0.1
        )


def test_empty_reference_fails(observations):
    with pytest.raises(ValueError):
        compare_spot_rates(
            observations.iloc[:0], observations.iloc[:0], tolerance_bp=0.1
        )


@pytest.mark.parametrize(
    "column,value",
    [
        ("maturity_years", -1),
        ("spot_rate_decimal", float("nan")),
        ("compounding", "unknown"),
    ],
)
def test_invalid_observation_fails(observations, column, value):
    invalid = observations.copy()
    invalid[column] = value
    with pytest.raises(ValueError):
        compare_spot_rates(invalid, invalid, tolerance_bp=0.1)
