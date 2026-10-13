# LIS yield curve reconstruction - Arnaud update, 13 October 2026

This addendum takes priority over the earlier starter's proposed directory
layout and local-only next-step prompt. It preserves the financial validation
requirements and the user's readable-code preferences.

## Confirmed instructions from Arnaud

In the user-pasted messages of 12 October at 23:36-23:37, Arnaud says US/German
data should be available. Portuguese parameters may not be available. Finding
them would be the easiest route; if unavailable, investigate estimation or a
different approach. This is not evidence that a complete search has established
their absence, or that a particular Portuguese calibration method is approved.

On 13 October at 13:35-14:13, Arnaud says he created the team repository,
provided the structure/files, and wants Manuel to clone it, create a new branch,
push progress to that branch and open a pull request when the code is ready.
Do not commit directly to main or merge the PR without a request to do so.

Repository: https://github.com/LISQUANT/yield-curve-reconstruction
Clone URL: https://github.com/LISQUANT/yield-curve-reconstruction.git

## Direct repository inspection in this session

Read the main branch on 13 October 2026. The repository is accessible through
the current connection. The README names US, Germany and Portugal.
The five Python files below currently contain module docstrings describing
their intended responsibilities; no implemented functions were present.
The recursive tree also contains README.md and the Python .gitignore template.
No AGENTS.md, tests or dependency configuration were present in that tree.
Repository tree SHA inspected: c3887563b330dd6432a12549c3528cb38e4d512a.
This is a tree SHA, not a claim about a checked-out commit or a later revision.

| Actual path | Intended role / observed description |
|---|---|
| yieldcurves/sources/fed.py | Download and gather the latest Fed Svensson parameters |
| yieldcurves/sources/bundesbank.py | Download and gather Bundesbank Svensson parameters |
| yieldcurves/svensson.py | Evaluate six parameters into spot and forward rates |
| yieldcurves/plots.py | Plot US and German curves for one date on one chart |
| make_report.py | Load parameters, choose latest common date, evaluate and save chart/CSV |

The make_report.py description already specifies a latest common date for
US/Germany. Treat that as evidence for the initial snapshot workflow. A full
historical daily pipeline remains an extension to confirm.
The bundesbank.py file makes Bundesbank the specified German provider. Preserve
the earlier ECB-universe distinction, but do not block this implementation
waiting for the old ECB-vs-Germany question: the current scaffold resolves the
initial source choice. If later asked for ECB AAA, label it as a separate benchmark.

## Relationship to work already completed locally

The latest uploaded model/status/handoff reports say the mathematical core was
retained, 43 tests passed, an isolated environment was checked, and a synthetic
example was reproduced. Those are reported results from the other local session;
this addendum has not rerun that Windows checkout or inspected its changed tests.
Locate that actual working copy before migrating anything. Do not substitute
the original 26-test ZIP and silently discard the newer tests or --output-dir.

Proposed migration, subject to inspecting the current actual code:
- Pure NSS calculations from src/lis_curves/model.py into yieldcurves/svensson.py.
- Preserve the existing tests and update imports to the actual package layout.
- Keep the synthetic teaching example separate from production data.
- Add a small validation helper only where the scaffold needs it.
- Add dependency metadata, package initialisation and tests as justified, without
  replacing the repo with a second src/lis_curves tree or a large framework.
- Keep downloads in sources/, plotting in plots.py, and orchestration in
  make_report.py. Reuse the numerical core rather than implementing NSS twice.

## Copy this prompt into Codex

```text
Update our LIS Quantitative Research project with Arnaud's instructions below.
Explain decisions in Spanish; keep code and team documentation in clear English.

The canonical repository is:
https://github.com/LISQUANT/yield-curve-reconstruction

Arnaud created its structure on 13 October. He explicitly wants me to clone it,
create a new branch, push progress to that branch, and open a pull request when
the code is ready. Use that workflow. Do not commit directly to main or merge
the PR automatically.

First inspect the current repository, README, guidance and actual file contents.
The scaffold observed in the previous review was:
yieldcurves/sources/fed.py
yieldcurves/sources/bundesbank.py
yieldcurves/svensson.py
yieldcurves/plots.py
make_report.py

Respect those paths and responsibilities. The files were descriptive stubs when
last inspected; check their current state before editing. Do not replace the
team layout with the starter's originally proposed src/lis_curves architecture.

Locate my latest local work under Documents/ChatGPT/Quantitative Research
Projects, using the actual path on this computer. Read its status, handoff,
model_review and verification_model. The latest reports say 43 tests passed
and the synthetic example supports --output-dir. Preserve those improvements.
If that directory is unavailable, request the exact path or files and continue
the independent repository review. Never claim to have read unavailable files.

Check Git status and origin before changing anything. If the local starter is
an independent repository with no remote, clone the canonical repository into
a separate folder and migrate reviewed files. Do not overwrite local changes,
attach unrelated history to the team remote or push the old starter wholesale.
Create a feature branch based on the current team default branch; reuse an
existing appropriate feature branch if it already belongs to this repository.
A suggested name is feature/manu-yield-curves.

Adapt the existing mathematical core into yieldcurves/svensson.py. Preserve its
stable small-maturity behaviour, decimal beta units, taus/maturities in years,
explicit compounding, discount factors and forward relationships. Preserve and
run the relevant tests after updating imports. Keep the model independent of
downloads, plotting and file writes.

Then carry out the Fed stage within yieldcurves/sources/fed.py. Retrieve or
explicitly import an authentic Fed snapshot, store provenance, select a complete
date and reconstruct using the existing model. Reconcile spot rates with the
same-date SVENY references and justify tolerances from published precision.
Treat Fed institution-hosted research data according to its source description;
do not call it a Board statistical release if the page says otherwise.

Use yieldcurves/plots.py for plotting. Use make_report.py as the entry point
that calls the modules and exports results. Once Bundesbank is implemented,
make_report.py must use the latest common complete US/German date, as the
existing scaffold describes. Until then, show a supported US-only result or
explicitly report Germany pending; never fabricate the second curve.
Implement Germany subsequently in yieldcurves/sources/bundesbank.py, checking
native compounding and published spot references. The current team scaffold
specifies Bundesbank, so the earlier ECB source question does not block this.

For Portugal follow Arnaud's order: first search for usable published parameters
or a suitable official zero-coupon curve; if found, verify the method and source.
If not found after a documented search, propose estimation or a different
approach based on actual data coverage. A missing public curve does not by itself
prove no data exist anywhere. Do not invent parameters, substitute coupon-bond
YTM for spot rates, or choose a final Portuguese calibration method without a
documented decision. Continue independent US/German work in the meantime.

Keep financial/model tests, official reconstruction comparisons and future
Portuguese calibration diagnostics distinct. Maintain readable functions,
intuitive names and short useful comments; no decorative or numbered banners,
redundant explanations or unnecessary framework. Keep licensed quotes,
credentials, environments and caches out of Git.

After a coherent verified stage, make a descriptive commit and push only the
working feature branch so Arnaud can review progress. If remote authentication
is unavailable, keep the work/commit local and explain the precise blocker;
do not ask for passwords or tokens in chat. When the implemented scope is ready
for review, open a pull request to the team default branch with the actual scope,
validation evidence and limitations. Do not claim all three curves are done if
the PR covers only US/Germany, or open duplicate PRs for the same branch.

Update PROJECT_CONTEXT, status, decisions, handoff, architecture and relevant
prompts to reflect the canonical repository, real file paths, branch workflow,
current source choices and Portuguese uncertainty. Retain earlier verification
records as historical evidence, not proof of the new checkout's results.

Keep the final technical PDF connected to one run's tables, plots, validation
and metadata. Generate code excerpts from the real files. make_report.py is
currently intended to orchestrate chart/CSV output; a final PDF needs an explicit
report generation step using those outputs. Do not pretend the stub already
generates a finished PDF. Original synthetic PDFs remain learning prototypes
until replaced with validated source data.

For this session, complete repository integration and the bounded Fed stage.
Explain the changed files, run the appropriate checks, show what the data mean,
and record the next German task. Do not wait to finish Portugal before showing
verified US progress on the feature branch.
```

## Evidence and scope of this update

Source: user-pasted Arnaud messages plus direct read-only inspection of the
canonical GitHub repository. No source implementation, commit, push or PR was
performed by this instruction-update session. No desktop access is inferred
from repository access. The earlier original package/PDFs are historical;
this addendum should be supplied alongside the latest local working copy.
