# Yield curve methodology

## Model and units

For maturity $t$ in years, define $L(x)=(1-e^{-x})/x$ and
$C(x)=L(x)-e^{-x}$. The Nelson-Siegel-Svensson spot curve is

$$y(t)=\beta_0+\beta_1 L(t/\tau_1)+\beta_2 C(t/\tau_1)+\beta_3 C(t/\tau_2).$$

Betas are decimal rates; positive taus are years. At zero, $L(0)=1$,
$C(0)=0$, and $y(0)=\beta_0+\beta_1$. The asymptotic rate is $\beta_0$.
The implementation uses `expm1` for the slope loading and, below $x=10^{-4}$,
$C(x)=x/2-x^2/3+x^3/8-x^4/30$ to avoid cancellation.

`SvenssonParameters` holds six validated constants. `spot_rate` accepts a scalar
or a NumPy array and returns the native-convention rate. `continuous_rate`
converts evaluated annual rates with `log1p`, never fitted beta coefficients.

## Discounting and forwards

For a continuous spot rate, $P(0,t)=\exp[-t y_c(t)]$. For an effective annual
rate, $P(0,t)=(1+y_a(t))^{-t}$ and $y_c(t)=\log[1+y_a(t)]$.
Thus $P(0,0)=1$ and

$$f(0,t)=-\frac{d\log P(0,t)}{dt}=y_c(t)+t y'_c(t).$$

In the continuous case this simplifies to

$$f(0,t)=\beta_0+\beta_1 e^{-t/\tau_1}
+\beta_2(t/\tau_1)e^{-t/\tau_1}+\beta_3(t/\tau_2)e^{-t/\tau_2}.$$

For an annual native curve the implementation instead computes
$\log(1+y_a)+t y'_a/(1+y_a)$. Negative rates are permitted. An annual rate at
or below -100% is rejected; discount factors greater than one are not rejected.
All exported forward rates are continuous. Every spot CSV records its native
compounding and includes a separate continuous-rate column.

## Dates and comparisons

A complete observation has six finite parameters, strictly positive taus and
all 30 published reference spots. Fed dates before 1980 are excluded because
the earlier specification uses a different restricted model. Daily source
calendars are intersected, then the latest complete date on or before the cutoff
is selected. No parameter is independently forward-filled. Fit quality never
determines the selected date.

Comparisons join on country, date, maturity and compounding. The signed error is
$10,000(y_{model}-y_{published})$ in basis points. Published curves are already
fitted: reproducing them is not an independent calibration or bond-price test.

## Rounding policy

The Fed reference tokens have four decimal places in percentage units, allowing
0.005 bp under nearest rounding. Bundesbank reference tokens have two, allowing
0.5 bp. These are export-precision assumptions, not institutional guarantees.
The source readers reject unexpected precision rather than widening tolerances.

Let $h_i$ be half the last printed parameter digit, after converting betas to
decimals. Since $L(x)=\int_0^1e^{-ux}du$, $|L'(x)|\leq 1/2$ and
$|C'(x)|\leq3/2$. A conservative rate error bound is

$$\sum_{i=0}^3h_{\beta_i}
+\frac{t h_{\tau_1}}{(\tau_1-h_{\tau_1})^2}
\left(\frac{|\beta_1|+h_{\beta_1}}2+\frac32(|\beta_2|+h_{\beta_2})\right)
+\frac{3t h_{\tau_2}(|\beta_3|+h_{\beta_3})}{2(\tau_2-h_{\tau_2})^2}.$$

This is converted to bp and added to the reference half-step and a $10^{-9}$ bp
numerical allowance. The bound is intentionally conservative; passing it does
not imply that rounding is the only cause of a residual.

For 2026-10-02, Germany's one-year spot differs by -0.527980537 bp, versus a
0.504488148 bp allowance. The other 29 German maturities and all 30 US
maturities pass. The one-year difference is not explained by this bound and
remains unresolved. The pipeline retains the observation and exits with code 2
after producing a report that identifies the exception.

## Interpretation

The grid contains 301 maturities from zero to 30 years. Below one year it is
extrapolation relative to the reference grid. Cross-country plots convert both
curves to continuous rates, but the USD-EUR difference is not a credit spread.
No forecasting, hedge performance, risk premium decomposition or price-fit
claim follows from the reconstruction exercise.


## Portuguese benchmark profile

Six daily BPstat yields are fitted in percentage units by a separate NS shape,
using four parameters and equal yield-error weights. The objective is the sum
of squared errors in basis points, 100 times each percentage-point residual.
Six points do not meet the minimum eight-observation screen for NSS. Results are
restricted to observed 2–10Y support. Multi-start and interior-exclusion checks
are descriptive stability screens, not confidence intervals. See
[Portugal](portugal.md) for the inputs, bounds and actual diagnostics.

No benchmark yield is passed to discounting or instantaneous-forward functions.
The implemented Portuguese price calibration instead discounts contractual cash
flows from settlement; it still awaits a verified empirical price panel.
The historical German double-rounding check in [German investigation](german_check.md)
is diagnostic only and does not alter the precision-derived validation policy.
