# German rounding investigation

Observation date: 2 October 2026. Review: 18 October 2026.

The preserved BBSIS snapshot passes its hash and series-identity checks. The
reconstruction uses the six daily ZST parameters for listed Federal securities,
with beta coefficients in percent and taus in years. It compares annual spot
rates with annual ZST.ZI references, not ZAR coupon yields or Pfandbriefe.

A fresh official API request for the six parameters and one-year reference
returned exactly the same observation tokens as the saved snapshot. The full
recheck responses and their acquisition records are retained in the local research
archive rather than this compact GitHub package. The numerical evidence is
summarized in `docs/german_check.json`.

An independent evaluation with Python Decimal at 50-digit precision gives:

| Quantity | Value |
|---|---:|
| Reconstructed annual spot (%) | 2.90472019462957638819 |
| Published annual spot (%) | 2.91 |
| Signed error (bp) | -0.5279805370423611 |
| Existing rounding allowance (bp) | 0.5044881478627063 |
| Decimal versus NumPy difference (bp) | 3.88e-14 |

The evaluated value rounds to 2.90%, not 2.91%. The 0.5 bp reference half-digit
plus the existing conservative parameter rounding bound does not cover this
observation. Floating-point arithmetic is not the explanation. Applying a
continuous-to-annual conversion to these already annual rates would compare a
different quantity and is not a justified correction.

The exact cause remains unestablished. The recheck provides no evidence of a
revision to these seven source observations. A difference in source processing
or unpublished convention would need confirmation from the publisher. No source
value, date, model coefficient or tolerance was adjusted. The comparison stays
29/30 and exit code 2 distinguishes this exception from execution failure.

Official source: [Bundesbank daily Federal-security curves](https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570).
Annual convention: Schich (1997), section II.1, cited in `docs/data_sources.md`.

## Entire preserved history

`yieldcurves/rounding.py` reproduces the independent review over all 265 complete
dates from 2025-10-01 through 2026-10-16. Each workflow run exports all 7,950
comparisons to `DE/rounding_history.csv` and counts to `DE/rounding_history.json`.
Decimal half-up rounding is used in percentage units, with zero relative tolerance
for equality checks. The original validation policy is evaluated separately.

| Check | Count |
|---|---:|
| Direct rounding to two decimals matches | 7,544 / 7,950 |
| First three decimals, then two, matches | 7,928 / 7,950 |
| Not explained by the latter rule | 22 |
| Original strict validation failures | 108 |
| Dates with at least one strict failure | 87 / 265 |

For 2 October, 2.904720... becomes 2.905 at three decimals and then 2.91 at two.
This explains how the displayed one-year value could arise without changing the
model. It does not establish that the Bundesbank uses this process. The evidence
is much broader than one tenor, but 22 exceptions remain and the publisher has
not confirmed the hypothesis. No message has been sent to the publisher.
