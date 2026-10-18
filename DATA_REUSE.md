# Included financial data and reuse

Reviewed 18 October 2026. Sources retain their own terms; this package does not
relicense source material or imply institutional endorsement.

| Source | Included material | Applicable conditions |
|---|---|---|
| Federal Reserve Board | data/example/US: original preamble, header and the unchanged 2026-10-02 CSV row; exact tokens also appear in regression fixtures and derived results | Board information is generally public domain unless otherwise indicated. Attribute the Board. The excerpt records the selection and full original-file hash. No excluded third-party material or institutional logo is included. |
| Deutsche Bundesbank | data/example/DE: 36 unchanged parameter/spot series files; associated provenance files; original recheck materials are kept locally, not in this package | Public ESCB statistics may be reused with source attribution and without modifying statistics or metadata. The third-party exception is not used as permission: these are Bundesbank-produced fitted curves. Original bytes remain unchanged; LIS calculations are separate. |
| Banco de Portugal BPstat | data/example/PT: six original JSON-stat replies and an exact-date transcription; the original six replies and a dated observation transcription; generated outputs are not included | BPstat's notice permits use of information obtained directly from the portal, subject to accurate reproduction, Banco de Portugal attribution and disclosure of modifications. Metadata retain LSEG as underlying source. Date selection and the indicative LIS NS fit are disclosed; neither is presented as an official spot curve. This is not a licence for a separate LSEG feed. |

Official notices:

- https://www.federalreserve.gov/disclaimer.htm
- https://www.bundesbank.de/en/homepage/user-information/terms-of-use-regarding-the-reuse-of-escb-statistics-621188
- https://bpstat.bportugal.pt/avisos-legais

BPstat's JavaScript legal page was read directly in the browser during the source
review. Per-series replies contain no additional reuse restriction identified in
that review. Source links, retrieval times, identities, units and SHA256 hashes
are retained. The Bundesbank and BPstat raw replies have not been edited. The BPstat metadata identify LSEG as an underlying source; the portal notice alone may not settle any separate third-party rights. Confirm the scope of reuse before publishing a public repository if in doubt.

No Investing.com observations, Bloomberg/MTS/Euronext exports or restricted
Portuguese price panel are included. External research papers and source PDFs
are linked rather than redistributed. Acquisition/import instructions are in
docs/data_sources.md and docs/portugal.md. The Fed downloader has encountered
HTTP 403; the included documented excerpt permits the historical offline run.
A future licensed price panel must be acquired separately with suitable rights.
