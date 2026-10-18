# Source data

Original full downloads are retained locally in `data/raw`; the small reproducible
bundle is in `data/example`; `data/snapshots.json` pins the
folders used by the workflow. Readers check the recorded SHA256 hashes before
reconstruction. A checksum establishes integrity, while the official acquisition
URL and retrieval record establish provenance. Refreshes create new folders.

## United States

[Federal Reserve nominal curve](https://www.federalreserve.gov/data/nominal-yield-curve.htm)
and its [CSV](https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv).
Methodology: [Gurkaynak, Sack and Wright, FEDS 2006-28](https://www.federalreserve.gov/pubs/feds/2006/200628/index.html).

The source is a Fed staff research product for off-the-run nominal Treasury
coupon securities, not an official Board statistical release. Use BETA0-BETA3,
TAU1-TAU2 and continuous zero-coupon SVENY01-SVENY30. SVENPY par yields are not
substitutes. Betas and yields are percentages; taus are years.

The saved original CSV was acquired from the official browser download on
2026-10-12 at 18:04:52 UTC, contains 17,038 dates and ends on 2026-10-02.
SHA256: `2ebdb0a0e94c586445ab9255c7c2d4809f2cdb3776493388453ebb9587ec4342`.
Direct download still returned HTTP 403 on 2026-10-18. No replacement data were
invented. The acquisition CLI remains available for a future download or import:

```console
python -m yieldcurves.sources.fed --download --output-dir data/raw/fed/new_snapshot
python -m yieldcurves.sources.fed --import-file downloaded.csv --expected-sha256 HASH --output-dir data/raw/fed/imported
```

For an import, calculate the hash of the file obtained from the official page
and preserve that acquisition evidence. Unknown retrieval times remain null;
the time of a local import is not represented as the original download time.

## Germany

[Bundesbank daily federal-security curves](https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570)
links directly to the BBSIS CSV API. The snapshot downloaded on 2026-10-18 covers
2025-10-01 to 2026-10-16, including missing calendar dates. It has 265 complete
observations. All 36 raw files and individual URL/time/hash records are retained.

Six parameter series use `BBSIS.D.I.ZST.{B0,B1,B2,B3,T1,T2}.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A`.
The 30 spot series use `BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.RnnXX.R.A.A._Z._Z.A`,
where `nn` is 01 through 30. The `ZST` classification is essential; `ZAR` describes
coupon-bearing yields, while other issuer/security codes describe different universes.

Example endpoint:
`https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZST.B0.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en&startPeriod=2025-10-01`.

The six coefficients are printed to five decimal places; reference spots to two.
The parser validates series identities, daily frequency, precision, flags, missing
observations and duplicate dates. It rejects flagged nonmissing values for review.
The common-date run uses 2026-10-02 and reports the unresolved one-year exception.

[Schich (1997), Estimating the German term structure](https://www.bundesbank.de/resource/blob/622394/f917db9f2fe9168243f272b535d67858/mL/1997-10-01-dkp-04-data.pdf),
section II.1, printed page 4, specifies discrete annual discounting for the
estimation. The current daily table describes Federal bonds, five-year notes
and Treasury notes with remaining maturity of at least three months. Raw source
PDFs and their provenance are retained in `data/references`.

## Reproducibility boundaries

The default workflow uses pinned snapshots and does not silently replace them
with fresher data. `--refresh` attempts downloads and reports failures; an older
snapshot is retained explicitly. The refreshed German window begins 366 days
before the requested cutoff. For earlier dates obtain a snapshot with sufficient
coverage; the workflow rejects an empty date intersection rather than extrapolating
through time. Network and provenance failures are distinct from comparison failures.

The small `tests/fixtures/official_reference.json` file contains exact numeric
tokens for 2026-10-02, with hashes and identifiers of the original snapshots.
It is a source transcription for regression testing, not the acquisition dataset.
Other parser fixtures are synthetic and explicitly labelled.

## Portugal and reuse

Six daily BPstat series, 12099454–12099459, supply fixed-rate Portuguese
Treasury benchmark yields at 2, 3, 4, 5, 7 and 10 years. The exact 2026-10-02
observations and original responses are in `data/example/PT`. See
[Portugal](portugal.md) for units, source checks and the indicative fit.

Reuse notices were reviewed on 18 October 2026:

- [Federal Reserve](https://www.federalreserve.gov/disclaimer.htm): Board material is generally public domain unless otherwise marked; cite the source. The bundled file preserves the original preamble, header and one date row. Its provenance includes the full parent-file hash and explicitly records the extraction.
- [Bundesbank](https://www.bundesbank.de/en/homepage/user-information/terms-of-use-regarding-the-reuse-of-escb-statistics-621188): publicly released ESCB statistics may be reused with attribution and without altering statistics or metadata; third-party data are excluded. These are Bundesbank fitted Federal-security series. All 36 source files remain byte-identical. LIS calculations are separate outputs.
- [BPstat](https://bpstat.bportugal.pt/avisos-legais): information obtained directly from the portal may be reused with accurate reproduction, Banco de Portugal attribution and disclosure of modifications. The original JSON-stat replies are unchanged; date selection and the LIS fitted curve are explicitly identified. Metadata retain the underlying LSEG attribution.

No vendor export, Investing.com table, credentials or restricted price panel is
included. The example bundle is about 353 kB, includes 265 complete German dates
for the rounding diagnostic, and permits the default historical run without
network access. It is a pinned research snapshot, not a current-data service.
