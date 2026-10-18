# Reading the model

Start with `yieldcurves/svensson.py`. `SvenssonParameters` holds four rate
coefficients and two decay times. `spot_rate` evaluates the formula; it does
not estimate parameters. Betas are decimals: 0.03 means 3%, not 0.03%.

For a continuous rate of 3% at five years, the discount factor is
exp(-5 * 0.03), approximately 0.860708. A payment of 100 at that time is worth
86.0708. A coupon bond is the sum of the present values of every remaining
coupon and redemption payment. That is what `bond_prices` calculates.

Next read `reconstruction.py`. The US and German functions load already
published parameters, evaluate the curve, and compare it with the institution's
published spot rates. They do not fit the underlying bonds. Germany publishes
annual rates, so the comparison uses annual rates; cross-country plots convert
the evaluated rates with log(1 + y), not the beta coefficients.

Read `sources/bpstat.py` and `benchmarks.py` for the actual Portuguese result:
six daily benchmark yields are checked against original replies and fitted
with an indicative NS shape. The output never enters pricing or discounting.

Then read `calibration.py`. The optional Portuguese price route reverses the problem: prices and payments
are inputs, and the six parameters are unknown. `fit_prices` changes the parameters
to minimize squared price differences. Several initial guesses reduce dependence
on one starting point. Different parameter sets can produce similar prices, so
small residuals alone are not enough to trust a fitted curve.

`yieldcurves/sources/portugal.py` checks the imported panel. Clean price plus
accrued interest gives dirty price. Payment amounts must already include the
correct entitlement and redemption. The model discounts from settlement using
actual days divided by 365. This time convention does not replace the coupon's
accrual convention.

Finally read `workflow.py`: acquire snapshots, select a common date, reconstruct,
compare, export and report. Portugal is optional and its settlement-based curve
is saved separately. The report distinguishes missing data, published-rate
comparisons and in-sample price fits.

Run `python -m pytest -q` before experimenting. The price-calibration fixtures are
synthetic and only check software behaviour. `tests/test_bpstat.py` also checks
the genuine Portuguese observations and the separate indicative fit. The genuine US/German regression
is in `tests/test_workflow.py`. The German exception is retained deliberately:
changing a tolerance to remove it would change the research criterion.

For a safe numerical experiment, change a parameter in `examples/first_curve.py`
and inspect its effect on spots and forwards. Do not edit the preserved source
snapshots. Study the tests for zero maturity and analytic forwards alongside
the corresponding equations in `docs/methodology.md`.
