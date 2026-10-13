# Decisions

Updated 13 October 2026 under CODEX_ARNAUD_UPDATE.md.

| Decision | Current position / evidence |
|---|---|
| Canonical layout | Arnaud's five-module scaffold retained; no src/lis_curves tree |
| Publishing | User authorizes feature-branch progress and PR; never main or automatic merge |
| Model | Migrated current core; AST identical; all prior 57 tests retained |
| Fed | Published parameters, not bond recalibration; SVENY continuous spot references |
| Acquisition | Bounded urllib download; 403 ends immediately; official browser/local-import fallback |
| Import evidence | Checksum verifies integrity; source authenticity depends on acquisition evidence |
| Date | Latest complete post-1979 NSS date with all 30 references on/before cutoff |
| Rounding | Observed 4-decimal percentage nearest rounding gives 0.005 bp, plus parameter bound and 1e-9 bp numerical allowance |
| Germany | Bundesbank selected by scaffold; old ECB-versus-Germany question no longer blocks it |
| Common date | Latest complete common US/DE date once both providers exist; current scope US only |
| Portugal | Search published parameters/official zero curves first; then documented alternatives if necessary |
| PDF | Deferred; original synthetic PDFs are teaching prototypes |

The rounding rule is an explicit export-precision assumption, not a Fed accuracy
warranty. Do not widen it to hide mismatches. Future changes record evidence,
alternatives and whether reviewer approval actually exists.
