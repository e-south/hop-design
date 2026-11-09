# Choose the verification boundary

Test categories describe the responsibility being protected. Test count alone
does not describe coverage of molecular sequence space.

| Responsibility | Question answered | Typical evidence |
| --- | --- | --- |
| Molecular rules and contracts | Are bases, cuts, pairing, chemistry, coordinates and identities correct? | Unit/property/contract checks, including invalid and contradictory inputs. |
| Workflows and trust boundaries | Does the same request reach a complete, portable preparation, and does altered saved evidence fail? | Discovery, continuation, CLI/API selection, retrieval and fresh admission/replay. |
| Presentation | Does the view faithfully show the recorded molecule and keep the user's selection? | Projection contracts, SVG/PDF inventories, layout, exact bases and browser interaction checks. |
| Repository integrity | Are modules, documentation, dependencies and public boundaries coherent? | Strict preflight, lint, types, documentation and privacy checks. |
| Distribution | Does the built and installed utility contain the required assets and reproduce its public behavior? | Clean installation and source/wheel comparisons. |

Keep tests with their existing owners. The presentation selection lives in
`scripts/verification_tests.py`; extend it when a new view responsibility is
introduced. It refuses stale or empty selections. The complete source gate
still collects every test.

```bash
bash scripts/agent-verify --scope presentation
bash scripts/agent-verify --scope source --workers 2
bash scripts/agent-verify --workers 2 --distribution routine
bash scripts/agent-verify --workers 2  # extended distribution qualification
# Match hosted coverage on a machine with four available cores:
UV_PYTHON=3.14 COVERAGE_CORE=sysmon bash scripts/agent-verify --workers 4
```

Choose one command for the task; do not run these gates in sequence.

- **Repository-only maintenance:** for documentation and repository checks when
  runtime source, packaged assets, dependencies, build rules and verification
  routing are unchanged. Run strict preflight, the affected checker regression
  tests and lint on changed files. Run the checker against the real repository
  as well as its rejection examples. Record this as focused repository
  verification, not a source or distribution gate. Changes to verification
  routing follow the runner rule below; changes to installed behavior use the
  appropriate scope below.
- **Presentation:** for rendering, molecular projection, typography, layout and
  browser-only changes. Run the changed view's positive and negative checks,
  visually inspect the actual export, and verify that its molecular inventory
  is conserved. This scope runs the declared view tests, every browser-model
  check, strict preflight, lint and type checks. It does not assert whole-source
  coverage or installed-package equivalence.
  Deriving new molecular facts, changing coordinate meaning or altering product
  identity requires source verification even if the result appears in a plot.
- **Source:** for models, molecular rules, request interpretation, search,
  persistence, identity, admission or handoff changes. It runs the entire Python
  suite with the existing 90% coverage floor, all browser checks and repository
  checks. Uncertain change impact also requires the full gate below.
- **Full:** source verification plus dependency audit and installed-distribution
  verification. `--distribution routine` builds and scans the wheel/sdist,
  compares every packaged source/asset byte with the checkout, installs only
  runtime dependencies in an isolated environment, and exercises discovery,
  reopening, a complete preparation, exact API/CLI oligos and PDF/SVG output.
  It reuses the existing public example. `--distribution extended` (the default)
  retains the complete source/wheel workflow comparisons. Use extended for
  packaging, dependencies, CLI wiring, asset inclusion, verification changes,
  releases or uncertain impact. CI selects the mode below. A manuscript-only
  change in a consumer repository uses that owner's checks.

## Installation qualification and runner changes

The routine installation emits stage names, elapsed times and separate logs into
one create-only directory below `.artifacts/verification/`. Each stage has a
five-minute deadline; failure or timeout stops qualification and cleans its
process group. Successful temporary environments and molecular outputs are
removed. The small gate took about 44 seconds locally with cached dependencies.
Full-suite and hosted timings require separate measurements; the source
suite remains the larger cost.

The extended runner labels its workflow groups and reports elapsed time and the
failed group. Its expensive parity cases run only in extended mode. We keep
those reference executions self-contained rather than introducing cross-run
pytest evidence caches; small archive/asset assertions and the public design
case are shared by both modes. No scientific source tests were removed.

Verification-runner changes need the routing/failure tests in
`tests/repo/test_verification_scopes.py` and the affected real scope. A stubbed
runner test proves command selection and failure propagation, not molecular
behavior. A narrowed scope must be named in the handoff; it must not be reported
as a full gate.

## Hosted CI policy

Pull requests run the complete source suite on Python 3.14 with branch coverage,
using coverage.py's lower-overhead `sys.monitoring` core. The 90% floor and test
membership are unchanged. Python 3.12 and 3.13 remain supported;
their contract and integration suites run through the separate
`python-compatibility.yaml` workflow on explicit dispatch and during release.
Release publication depends on both compatibility and exact-distribution checks.
Dispatch compatibility for changes that may break an older interpreter. The
repository's local Python default and minimum requirement remain 3.12; the command
above selects the faster coverage runtime without changing a deployed runtime.

Main requires an up-to-date pull request with successful `Checks`, dependency
review and CodeQL, including for administrators. CI therefore does not repeat
the full suite on the subsequent squash-merge push. Manual dispatch remains a
complete verification path. This relies on those branch protections: restore
push verification before permitting direct or unchecked main updates. Release
still qualifies its exact wheel/sdist and supported Python versions. Coverage
reports come from PR qualification; there is no separate post-merge report.

The coverage choice was measured on one exhaustive-completion/replay test using
three alternating fresh-process trials per condition (macOS arm64,
coverage.py 7.15.4, the same locked dependencies):

| Runtime and coverage core | Median wall time | Trial range |
| --- | --- | --- |
| Python 3.12.11, CTracer | 95.10 s | 91.14–96.62 s |
| Python 3.14.7, CTracer | 104.03 s | 100.95–110.11 s |
| Python 3.14.7, SysMonitor | 66.45 s | 64.70–68.04 s |

All nine trials passed the same scientific assertions. Python 3.14's two cores
recorded identical executed/missing line and branch sets in every trial; changing
the interpreter alone was slower. The adopted combination reduced this sample's
time by 30.1%, not a claimed full-suite speedup. The node is
`tests/integration/test_survey_completion_execution.py::test_public_completion_matches_exhaustive_product_choices_with_fewer_attempts`;
run it with `--cov=hop_design --cov-branch --cov-report=json` and the declared
`COVERAGE_CORE`. A subset benchmark needs `--cov-fail-under=0`; the full gate
retains 90%. Coverage.py documents the
[core selection and Python requirements](https://coverage.readthedocs.io/en/7.15.4/config.html#run-core).

`scripts/ci_scope.py` limits the smaller merge gate to its exact README/banner
path allowlist. It checks the complete changed-path set, including both sides of
renames. Empty, mixed, unknown, or unavailable comparisons require the full gate;
invalid revisions or a failed diff stop verification. For full verification,
ordinary Python source, tests and documentation Markdown use routine installation.
Documentation includes guides, known root Markdown contracts, Markdown below
`.agents/` and `examples/`, and `.github/pull_request_template.md`. This changes
the installed-distribution check only; the complete source suite still runs.
Packaging/dependencies, CLI entry points, packaged assets (including their
Markdown), scripts, workflows, non-Markdown files under `examples/` or `.agents/`,
unknown paths or missing comparison evidence use extended installation.
Mixed changes take the stronger mode. Manual CI always uses extended. Both
outputs are checked before execution; a missing mode fails. The selector itself
therefore receives extended qualification before this policy can be merged.

The README/artwork gate runs strict preflight, repository lint and workflow
validation, CI contract tests, distribution builds and metadata checks. Review
the banner visually as well. This gate establishes repository and packaging
integrity, not molecular replay or installed-package parity. Packaged browser
assets and molecular figures do not qualify for this exception.

The stable `Checks` job remains required for both scopes and rejects a failed,
canceled or skipped verification job. The workflow itself is never path-skipped;
that would leave required checks pending. The full gate still produces coverage;
artwork-only runs do not upload or replace that report.

## Use bounded parallelism

`--workers 2` or `--workers 4` runs a bounded number of Python worker processes
with `loadscope`; the default is serial. This keeps module/class fixture groups
together and avoids unbounded CPU/memory expansion. A session fixture is still
instantiated in each worker that needs it. Hosted CI uses four workers on the
public Ubuntu runner's four CPUs and 16 GB RAM; local callers choose a smaller
count when sharing the machine. Compare identical test membership and record
wall time and process-tree memory before increasing concurrency.
[GitHub runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[pytest-xdist distribution](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
and [fixture lifetime](https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once)
describe that behavior. Coverage from workers is combined by
[pytest-cov](https://pytest-cov.readthedocs.io/en/stable/xdist.html).

Both source and presentation runs save JUnit timings in `.artifacts/verification/`
and print their slowest tests. Every gate stage reports its start, duration and
exit status in the log and `stages.tsv`, retained by CI even on failure. Strict
preflight checks API exports and CI/documentation contracts before the expensive
source suite. Lint and formatting run once through the repository hooks.
The full gate audits hashed locked requirements, including development and
optional dependencies, before scientific tests. This catches dependency failures
early instead of running the source suite first. The isolated installation still
contains only the declared runtime dependencies.
Compare setup with call cost: constructing a broad
fixture is different from repeatedly reopening its authorities. Profile a slow
case with `python -m cProfile -o ... -m pytest path::test` and measure ordinary
timings separately. CPU-bound replay should be addressed before adding more
workers or weakening admission. Do not start duplicate gates; a failed scope
remains failed until repaired and verified.

An October 2026 local pilot used three fresh-process trials per worker count,
identical test membership and `loadscope` on Python 3.12/macOS arm64:

| Workload | Serial median | Two-worker median | Peak summed process RSS, serial → two workers |
| --- | --- | --- | --- |
| 19 atlas, inspection and print checks | 27.14 s | 24.00 s | 339 → 651 MB |
| Two discovery/retrieval/replay checks | 30.78 s | 20.90 s | 254 → 483 MB |

Two workers helped these samples but nearly doubled their memory footprint.
These timings do not predict a full-suite speedup: shared session fixtures are
repeated across workers, and module groups may have unequal costs. Serial remains
the portable default; two workers are an explicit option. Summed RSS includes
shared pages and is not a measurement of unique physical memory. Retain the
commands, individual trial results and environment with a performance review.

A separate November 2026 pilot compared two and four workers on four discovery,
checkpoint upgrade/resume and CLI/API handoff tests (Python 3.14.7/SysMonitor,
macOS arm64, three alternating trials, unchanged `loadscope` grouping):

| Workers | Median wall time (range) | Median child CPU time | Maximum summed process RSS |
| --- | --- | --- | --- |
| 2 | 16.98 s (15.33–17.74) | 23.31 s | 602 MiB |
| 4 | 13.34 s (12.19–15.58) | 26.50 s | 996 MiB |

All 24 test executions passed; test membership and line/branch coverage matched.
Four workers reduced sample latency by 21.4% while using 13.7% more CPU time and
more memory. This is a latency choice within the hosted runner's capacity, not
an efficiency claim or a prediction for the full Linux suite. Local serial/two
worker options remain available.

Use small real constructions for corruption and boundary tests. Keep broad
populations for coverage, diversity and grouping tests. The shared read-only
GAAA/TTTC fixture serves query and projection tests; tests that mutate files copy
it first, and admission tests load it afresh. Share immutable setup, not acceptance
decisions between independent tests.

Pytest removes successful temporary test directories and retains three failed
sessions. `wheel-smoke` owns and removes its temporary environment. Keep profiles,
logs and reproducing inputs separate from generated preparations. Before removing
any older outputs, check their owner and reproduction role; age alone is not a
cleanup rule. Benchmark cleanup tests cover both errors and interruption.
