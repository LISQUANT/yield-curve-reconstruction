import math

import numpy as np
import pytest

from yieldcurves.svensson import (
    SvenssonParameters,
    continuous_rate,
    discount_factor,
    instantaneous_forward,
    spot_rate,
)


@pytest.fixture
def parameters():
    return SvenssonParameters(0.035, -0.015, 0.012, -0.006, 1.8, 7.0)


def test_short_and_long_limits(parameters):
    assert spot_rate(0, parameters) == pytest.approx(0.02)
    assert spot_rate(1e-12, parameters) == pytest.approx(0.02, abs=1e-12)
    assert spot_rate(1e8, parameters) == pytest.approx(0.035, abs=1e-8)
    assert discount_factor(0, parameters, compounding="continuous") == 1


def test_fixed_reference_value(parameters):
    # Ordinary scalar arithmetic is independent of the vectorised loading helper.
    x1, x2 = 5 / 1.8, 5 / 7.0
    slope1 = (1 - math.exp(-x1)) / x1
    slope2 = (1 - math.exp(-x2)) / x2
    expected = (
        0.035 - 0.015 * slope1
        + 0.012 * (slope1 - math.exp(-x1))
        - 0.006 * (slope2 - math.exp(-x2))
    )
    assert expected == pytest.approx(0.03189043225529862, abs=1e-15)
    assert spot_rate(5.0, parameters) == pytest.approx(expected, abs=1e-15)
    assert spot_rate(5.0, parameters) == pytest.approx(0.03189043225529862, abs=1e-12)


@pytest.mark.parametrize("compounding", ["continuous", "annual"])
def test_zero_and_tiny_maturities_without_warnings(parameters, compounding):
    years = np.array([0.0, 1e-15, 1e-12])
    with np.errstate(all="raise"):
        spots = spot_rate(years, parameters)
        discounts = discount_factor(years, parameters, compounding=compounding)
        forwards = instantaneous_forward(years, parameters, compounding=compounding)
    # First-order limits include the genuine slope at a small positive maturity.
    spot_slope = (0.015 + 0.012) / (2 * 1.8) - 0.006 / (2 * 7.0)
    np.testing.assert_allclose(spots, 0.02 + spot_slope * years, rtol=0, atol=1e-16)
    assert discounts[0] == 1
    short_forward = 0.02 if compounding == "continuous" else math.log1p(0.02)
    forward_slope = 2 * spot_slope
    if compounding == "annual":
        forward_slope /= 1.02
    np.testing.assert_allclose(
        forwards, short_forward + forward_slope * years, rtol=0, atol=1e-16
    )


def test_annual_discount_uses_evaluated_spot(parameters):
    years = np.array([1.0, 5.0, 30.0])
    native_spots = spot_rate(years, parameters)
    np.testing.assert_allclose(
        discount_factor(years, parameters, compounding="annual"),
        (1 + native_spots) ** (-years),
        rtol=1e-14,
    )


def test_flat_curve():
    p = SvenssonParameters(0.04, 0, 0, 0, 1, 4)
    years = np.array([0, 1, 5, 30])
    np.testing.assert_allclose(spot_rate(years, p), 0.04)
    np.testing.assert_allclose(
        discount_factor(years, p, compounding="annual"), (1.04) ** (-years)
    )
    np.testing.assert_allclose(
        instantaneous_forward(years, p, compounding="annual"), np.log1p(0.04)
    )


@pytest.mark.parametrize("compounding", ["continuous", "annual"])
def test_forward_is_log_discount_derivative(parameters, compounding):
    years = np.array([0.1, 1, 5, 10, 30])
    h = 1e-5
    upper = discount_factor(years + h, parameters, compounding=compounding)
    lower = discount_factor(years - h, parameters, compounding=compounding)
    derivative = -(np.log(upper) - np.log(lower)) / (2 * h)
    np.testing.assert_allclose(
        instantaneous_forward(years, parameters, compounding=compounding),
        derivative,
        atol=1e-10,
    )


@pytest.mark.parametrize("maturity", [-1, np.nan, np.inf])
def test_reject_invalid_maturities(parameters, maturity):
    with pytest.raises(ValueError):
        spot_rate(maturity, parameters)


@pytest.mark.parametrize("tau", [0, -1, np.inf, np.nan])
def test_reject_invalid_parameters(tau):
    with pytest.raises(ValueError):
        SvenssonParameters(0.03, 0, 0, 0, tau, 1)


@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize("value", [np.inf, np.nan])
def test_every_parameter_must_be_finite(index, value):
    values = [0.035, -0.015, 0.012, -0.006, 1.8, 7.0]
    values[index] = value
    with pytest.raises(ValueError, match="finite"):
        SvenssonParameters(*values)


@pytest.mark.parametrize("tau2", [0, -1])
def test_second_tau_must_be_positive(tau2):
    with pytest.raises(ValueError, match="positive"):
        SvenssonParameters(0.03, 0, 0, 0, 1, tau2)


def test_negative_rates_and_conversion():
    p = SvenssonParameters(-0.005, 0, 0, 0, 1, 3)
    assert discount_factor(5, p, compounding="annual") > 1
    assert continuous_rate(0.04, "annual") == pytest.approx(np.log1p(0.04))
    with pytest.raises(ValueError):
        continuous_rate(-1, "annual")
    with pytest.raises(ValueError):
        continuous_rate(0.03, "unknown")


def test_vector_matches_scalar(parameters):
    years = np.array([0, 1e-12, 0.1, 5, 30])
    np.testing.assert_allclose(
        spot_rate(years, parameters), [spot_rate(t, parameters) for t in years]
    )
