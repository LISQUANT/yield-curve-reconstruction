# Reproducible historical source bundle

Observation date: 2 October 2026. Reviewed on 18 October 2026.

US contains the original Federal Reserve CSV preamble, header and exact date
row. Other dates were omitted; the extraction and full parent-file hash are
recorded in provenance.json. DE contains all 36 unmodified Bundesbank series
files, with 265 complete dates for the historical rounding investigation.
PT contains six unmodified Banco de Portugal BPstat replies and a checked
same-date transcription; metadata identify the underlying source as LSEG.

These are real institutional-source observations, not synthetic test inputs.
Derived curves are LIS calculations and are never presented as source releases.
See docs/data_sources.md for source links, reuse notices and transformations.
Default configuration is data/snapshots.json. Full local downloads and research
materials remain excluded from version control.
