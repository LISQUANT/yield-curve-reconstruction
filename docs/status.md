# Current status

Updated: 13 October 2026. Canonical repository integration and bounded Fed stage.

| Component | Status / evidence |
|---|---|
| Repository integration | Arnaud scaffold retained on codex/manu-fed-integration |
| Mathematical core | Preserved; AST equivalence to latest local core checked |
| Tests | 70 pass in fresh environment, including original 57; Ruff/pip check pass |
| Synthetic example | Reproduced separately; never market evidence |
| Fed real data | Authentic saved CSV; actual date 2026-10-02; 30/30 SVENY pass |
| Fed acquisition | Reproducible downloader implemented; live HTTP 403 persists; verified import works |
| Offline report | No-network replay passes; five output files identical |
| Germany | Bundesbank placeholder unchanged; next bounded stage |
| Portugal | Published-parameter/official-zero search first; not started here |
| Final Macro PDF | Deferred |

See verification.json and fed_validation.md. Historical records under history/
are not evidence of this checkout. Source snapshots and full run files are local.
Implementation commit f0aa7c7 is pushed to codex/manu-fed-integration.
[Pull request #1](https://github.com/LISQUANT/yield-curve-reconstruction/pull/1)
is open for review. Main remains unchanged; no merge has been performed.
