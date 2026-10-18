# Portugal: daily benchmark yields and price calibration

The verified empirical result is an **indicative Nelson–Siegel benchmark-yield fit**
for 2 October 2026, restricted to 2–10 years. It is not a zero-coupon curve.
The separate bond-price calibration remains available and tested.

## Verified BPstat observations

The six original JSON-stat replies were downloaded directly from Banco de
Portugal's HTTPS API on 18 October 2026. They are preserved in `data/example/PT/`
with URLs, retrieval timestamps, SHA256 hashes and an unchanged numerical
transcription. All six observations have status F, daily frequency, percentage
units and metric Average. The publisher is Banco de Portugal; metadata identify
LSEG as the underlying source. Do not describe these as closing prices or infer
a constant-maturity interpolation method that the retrieved metadata do not specify.

| Residual maturity | BPstat series | Yield (%) on 2026-10-02 |
|---|---|---:|
| 2 years | 12099454 | 3.28 |
| 3 years | 12099455 | 3.31 |
| 4 years | 12099456 | 3.45 |
| 5 years | 12099457 | 3.56 |
| 7 years | 12099458 | 3.73 |
| 10 years | 12099459 | 3.95 |

[BPstat daily series](https://bpstat.bportugal.pt/serie/12099456) and the
[legal notice](https://bpstat.bportugal.pt/avisos-legais) were checked directly.
The notice permits use of information obtained directly from BPstat, with
accurate reproduction, Banco de Portugal attribution and disclosure of changes.
The fitted line is an LIS calculation. This review concerns the BPstat files;
it does not grant access to or a licence for a separate LSEG feed.

The earlier review of table 484 identified monthly series only. It did not
establish that BPstat lacked daily observations; that conclusion is superseded.
No Investing.com observations are used. Their preliminary 2Y and 20Y/30Y issues
are irrelevant to these independently identified BPstat series.

## Reproduce or refresh

The default pinned bundle runs offline. To acquire a new, separate snapshot:

```console
python -m yieldcurves.sources.bpstat --date 2026-10-02 --output-dir data/raw/bpstat/new_snapshot
python scripts/run_yield_curves.py --offline --date 2026-10-02 --portugal-benchmarks data/raw/bpstat/new_snapshot
```

The downloader checks the exact date, series identity, frequency, source,
units, maturity and observation status. It retains original responses and writes
a complete manifest only after all six succeed. Failed downloads cannot be
loaded as complete snapshots. A different date is never filled or relabelled.
For manual import retain the six original API replies and the CSV/provenance
layout demonstrated in the included bundle; the reader checks the CSV against
the original observations as well as their hashes. Hashes establish integrity,
not authenticity independent of the acquisition record.

## Indicative fit

`yieldcurves/benchmarks.py` fits benchmark yields in percent with equal weights.
The existing five fixed starting values and bounded optimization are retained.
NS uses four parameters and requires at least six observations; NSS requires
eight. Six quotes do not justify a six-parameter Svensson fit with no residual
degrees of freedom. No points are invented beyond the observed 2–10Y support.

The selected NS fit has RMSE **1.308102 bp**, maximum residual **1.946545 bp**,
Jacobian condition **183.825**, and maximum interior-tenor exclusion change
**3.416773 bp**. Three starts converge near the best minimum; two reach a worse
solution near the tau upper bound. All starts are reported, not discarded from
the record. Near-best fitted curves differ by less than 0.00001 bp.

The pre-existing display screens require condition below 1e8, no active bound,
near-best start variation at most 2 bp, interior exclusion change at most 5 bp,
and fitting error at most 5 bp. Near-best means RMSE within 0.1 bp of the best.
These are transparent display rules, not statistical confidence intervals or
proof of parameter uniqueness. Deleting endpoints would change support, so only
interior tenors are tested. If no fit passes, only connected observations are
shown. A connected line's zero residual is an identity, not validation.

Outputs in `PT_benchmarks/` include original data, `indicative_curve.csv`,
`observations_and_residuals.csv`, all fit diagnostics and three figure formats.
They do not feed the discount, forward or bond-pricing functions and are not
included in the US/German zero-rate comparison. RMSE measures in-sample smoothing,
not agreement with an official Portuguese spot curve.

## Separate bond-price calibration

A suitable bond panel would include ISIN, price timestamp, settlement date,
currency, clean price per 100, accrued interest, redemption amount, coupon
frequency and full remaining payment schedule. Day-count and business-day rules
must be documented. Use comparable fixed-rate nominal Portuguese sovereign
bonds; avoid mixing observations from different auction or valuation dates.

For observed dirty price $P_i^{dirty}$ and known payments $CF_{ij}$ at times
$t_{ij}$ from settlement, a possible objective is

$$\min_{\theta}\sum_i w_i\left[
\sum_j CF_{ij}\exp(-t_{ij}y_c(t_{ij};\theta))-P_i^{dirty}\right]^2.$$

Positive taus, economically defensible parameter bounds, multiple starting
values, maturity coverage, price residuals and sensitivity to bond exclusions
are checked or recorded by the calibration, except exclusion sensitivity, which
remains a research check. Weights are explicit and are not adjusted to conceal poor fits.
Six parameters can be weakly identified even with many bonds; parameter stability
and fit quality are different questions. The optimizer is implemented and tested on explicitly synthetic fixtures. No
market parameter table is supplied until verified observations support estimation.

A euro-area aggregate curve is not a Portuguese sovereign curve. Coupon-bond
yield-to-maturity cannot be relabelled as a zero-coupon spot rate.


## Import and execution

The importer requires three files in one folder. Raw exports and their original
provider documentation should also be retained. A hash proves byte integrity,
not that a claimed price or payment schedule is economically correct; review the
source before using an import. No downloader for a complete Portuguese panel has
been verified.

`bonds.csv` has one row per bond with columns:

```text
isin,observation_date,settlement_date,currency,issuer,instrument_type,clean_price,accrued_interest
```

All rows must have the same observation and settlement dates. Currency is EUR,
issuer is `Republic of Portugal`, instrument type is `nominal_fixed_rate`.
Prices and accrued interest are amounts per 100 face value. The current importer
supports non-negative accrued interest and excludes ex-coupon adjustments.

`cashflows.csv` contains every remaining entitled payment, including redemption:

```text
isin,payment_date,amount
```

Amounts are per 100 face value. Combine coupon and principal on the same payment
date. Dates are YYYY-MM-DD. Use actual contractual payment dates after applying
the instrument's business-day rules. Do not generate coupon schedules by adding
365 days. The importer checks consistency, but cannot independently establish
that supplied schedules are complete. Accrued interest must follow the bond's
coupon day-count convention; ACT/365F below concerns discount times only.

`provenance.json` records these fields (replace descriptive placeholders):

```json
{
  "source_url": "https://provider.example/actual-export-reference",
  "retrieved_at_utc": "YYYY-MM-DDTHH:MM:SS+00:00",
  "observation_date": "YYYY-MM-DD",
  "settlement_date": "YYYY-MM-DD",
  "price_basis": "per_100_face",
  "curve_time_basis": "ACT/365F",
  "cashflow_conventions": "Actual accrual, calendar, payment and entitlement rules; source references",
  "data_kind": "market_observations",
  "sha256": {"bonds.csv": "actual SHA256", "cashflows.csv": "actual SHA256"}
}
```

Use a common price timestamp or a consistently defined daily close, and document
that convention with the export. Do not combine stale last trades as if they
were simultaneous closing prices. Preserve evidence of quote dates and sources.
The panel date must equal the workflow's selected US/German date:

```console
python scripts/run_yield_curves.py --offline --date YYYY-MM-DD --portugal-dir data/raw/portugal/DATE
```

The calibration needs at least seven distinct bond maturities, including one
within three years and one at least ten years away. These are minimum screening
rules, not evidence that six parameters are well identified. It minimizes equal
squared dirty-price errors. Beta bounds are [-0.05, 0.20] for beta0 and
[-0.30, 0.30] for beta1..3; taus are between 0.05 and 30 years. Negative rates
are allowed. Six fixed starting pairs make the numerical procedure reproducible.
Bounds are modelling assumptions and need review for a new market regime.

Outputs under `PT/` include `curve.csv`, `parameters.json`, `price_residuals.csv`,
`calibration_starts.csv`, `calibration.json`, original inputs, and a three-format
curve/price-error figure. Residuals are prices per 100, not yield basis points.
The diagnostics retain Jacobian rank, condition, bound warnings and results from
all starts. A good in-sample fit is not an official validation or proof of unique
parameters. Exclusion sensitivity, bid-ask consistency and economic plausibility
of forwards remain necessary before interpreting an actual fit.

The Portuguese curve's time origin is settlement. It stays separate from the
institutional comparison; changing its label cannot align valuation origins.
The report includes import fit statistics when a panel is provided. Default runs show the independently verified benchmark-yield fit; no price-calibrated zero curve is available.

