"""Svensson rates in decimal units, with maturities and taus in years."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

Compounding = Literal["continuous", "annual"]


@dataclass(frozen=True)
class SvenssonParameters:
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float

    def __post_init__(self):
        values = (self.beta0, self.beta1, self.beta2, self.beta3, self.tau1, self.tau2)
        if not np.isfinite(values).all():
            raise ValueError("Svensson parameters must be finite.")
        if self.tau1 <= 0 or self.tau2 <= 0:
            raise ValueError("Tau parameters must be positive, in years.")


def _maturities(maturity):
    years = np.asarray(maturity, dtype=float)
    if not np.isfinite(years).all() or (years < 0).any():
        raise ValueError("Maturities must be finite and non-negative, in years.")
    return years


def _loadings(x):
    slope = np.ones_like(x)
    np.divide(-np.expm1(-x), x, out=slope, where=x != 0)
    curvature = np.asarray(slope - np.exp(-x))
    small = x < 1e-4
    # The series retains curvature when subtraction loses precision near zero.
    xs = x[small]
    curvature[small] = xs / 2 - xs**2 / 3 + xs**3 / 8 - xs**4 / 30
    return slope, curvature


def spot_rate(maturity, parameters: SvenssonParameters):
    """Return the NSS spot rate in the parameters' native convention."""
    years = _maturities(maturity)
    slope, curvature1 = _loadings(years / parameters.tau1)
    _, curvature2 = _loadings(years / parameters.tau2)
    return (
        parameters.beta0
        + parameters.beta1 * slope
        + parameters.beta2 * curvature1
        + parameters.beta3 * curvature2
    )


def continuous_rate(rate, compounding: Compounding):
    """Convert rates, rather than fitted beta coefficients, to continuous units."""
    rate = np.asarray(rate, dtype=float)
    if not np.isfinite(rate).all():
        raise ValueError("Rates must be finite.")
    if compounding == "continuous":
        return rate
    if compounding == "annual":
        if (rate <= -1).any():
            raise ValueError("Annual rates must be greater than -100%.")
        return np.log1p(rate)
    raise ValueError(f"Unsupported compounding convention: {compounding}")


def discount_factor(maturity, parameters, *, compounding: Compounding):
    """Return exp(-T*r_continuous(T)); D(0) equals one."""
    years = _maturities(maturity)
    rate = continuous_rate(spot_rate(years, parameters), compounding)
    return np.exp(-years * rate)


def instantaneous_forward(maturity, parameters, *, compounding: Compounding):
    """Return -d log(D(T))/dT, expressed as a continuous decimal rate."""
    years = _maturities(maturity)
    x1, x2 = years / parameters.tau1, years / parameters.tau2
    native_derivative = (
        parameters.beta0
        + parameters.beta1 * np.exp(-x1)
        + parameters.beta2 * x1 * np.exp(-x1)
        + parameters.beta3 * x2 * np.exp(-x2)
    )
    if compounding == "continuous":
        return native_derivative
    if compounding == "annual":
        native_rate = spot_rate(years, parameters)
        converted_rate = continuous_rate(native_rate, compounding)
        return converted_rate + (native_derivative - native_rate) / (1 + native_rate)
    raise ValueError(f"Unsupported compounding convention: {compounding}")
