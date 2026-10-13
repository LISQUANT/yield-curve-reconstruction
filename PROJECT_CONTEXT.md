# Project context

Canonical repository: https://github.com/LISQUANT/yield-curve-reconstruction.
Current scope: integrate the reviewed local work into Arnaud's scaffold and finish
the Fed stage. The 13 October 2026 user request authorizes a feature branch,
verified progress pushes and a pull request. Earlier local-only restrictions are
superseded for this repository. No direct main commits or automatic merge.

CODEX_ARNAUD_UPDATE.md preserves the supplied instruction update. Its references
to 43 tests reflect earlier reports: the actual local source had 57 tests plus a
validated authentic Fed snapshot. All those tests were retained during migration.

Arnaud's scaffold specifies Svensson calculations, separate Fed/Bundesbank sources,
plots.py and make_report.py. Before migration the five files contained descriptive
docstrings only. Base commit c3887563b330dd6432a12549c3528cb38e4d512a was checked
out directly; the addendum's description of that identifier as a tree SHA is
historical and is not used as checkout evidence.

US reconstruction and source validation are now implemented. Germany is still a
stub, with Bundesbank selected by the team structure. Once implemented, make_report
must select the latest common complete US/DE date. Today it explicitly supports
US only. Full historical research is not part of this first snapshot workflow.

For Portugal, first seek usable published parameters or an official zero-coupon
curve. Their absence has not been established. If the documented search fails,
propose estimation or another approach using available data; no final calibration
method has been approved. Coupon-bond yields must not be relabelled as spots.

The final Macro PDF is later work built from a validated run, not from synthetic
teaching figures. Original prototype PDFs remain in the separate local starter.
Mathematics, acquisition, tables, plots and future reporting remain distinct.
