# Source and repository review

On 13 October 2026 the canonical repository was cloned at commit
c3887563b330dd6432a12549c3528cb38e4d512a. README, Python .gitignore and all five
Python files were read; files were responsibility docstrings, with no implemented
functions, tests, AGENTS.md or dependency metadata. The update's SHA was verified
as this commit, rather than relying on its earlier tree-SHA description.

Reviewed local work included model, comparison helper, Fed parser, offline report,
synthetic example with --output-dir and 57 tests. Migration uses this latest state,
not the original 26-test ZIP. Current checkout verification is separate from
historical records retained under docs/history.

LIS training inspected on 12 October: Session #6 p.4 and pp.51-57 supports separate
acquisition/calculation/reporting; Session #7 pp.25,37-38 cautions about premature
parallelism; Risk Management in Python.zip::test.py illustrates small functions
but has a personal path and unconditional main(); Quant_Class.py memory examples
contain top-level demos. These materials are not production-repository conventions
or verified Arnaud authorship. Course-wide coding comparisons remain unverified.

Fed source page and CSV preamble distinguish continuous SVENY from SVENPY par
yields. GSW Table 1 confirms conventions. See fed_validation.md for retrieval
method, immutable snapshot checksum, actual coverage and rounding assumptions.
No original teaching archives, chat exports or private course materials are copied
into this repository. CODEX_ARNAUD_UPDATE.md is the user-supplied instruction record.
