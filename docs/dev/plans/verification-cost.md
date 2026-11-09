# Remove duplicate verification work

Status: adopted in [PR 50](https://github.com/e-south/hop-design/pull/50), with
extended installation qualification. The subsequent routine gate for
[PR 51](https://github.com/e-south/hop-design/pull/51) passed 3,809 source tests,
browser checks and clean-install verification, with 90.87% source coverage.
API exports, documentation and CI contracts now run during strict preflight.
Full verification audits the hashed lock, including optional and development
dependencies, before starting scientific tests.

The adopted workflow removes duplicate lint and post-merge source-suite execution,
uses Python 3.14's lower-overhead branch-coverage core, and exposes per-stage
timings. Python 3.12/3.13 compatibility still gates release. Four-worker admission
is bounded and measured separately from coverage instrumentation; see the
[verification guide](../performance.md#use-bounded-parallelism). Scientific test
membership and the 90% coverage floor remain unchanged.

The goal is to run each scientific responsibility once in the main suite and
retain a small, independent check of the actual installed distribution. Success
removes repeated discovery and rendering from routine CI without losing exact
molecular, material, asset or command-line checks. It will not eliminate the cost
of the main test suite; measure installation verification separately.

## Evidence and scope

`tests/repo/test_public_scaffold_family.py` already executes the family and
continuation examples. `scripts/wheel-smoke` executes those examples again from
source and then from a clean installation. `tests/repo/test_docs_smoke.py` and
`test_construction_dogfood.py` also protect explicit commands in that script.
Some of those assertions preserve orchestration rather than the scientific
outcome. The separate installation still matters: checkout tests cannot establish
that runtime dependencies, packaged assets and entry points work without the
development environment.

Work belongs in HOP's verification scripts, existing tests, workflows and
maintainer guidance. Keep private application inputs and campaign operations
outside the tool. Do not change molecular rules, search permissions, runtime
validators, public API/CLI behavior, supported Python versions or coverage floors.
The previously running gate completed before this implementation began.

Python-matrix and README/artwork routing are part of the adopted workflow.
Future changes still require the appropriate protected gate before merging.

## Verification responsibilities

| Boundary | Retain | Avoid repeating |
| --- | --- | --- |
| Main source suite | Molecular rules, discovery, continuation, valid/invalid inputs, identities, rendering and browser tests | A second source execution solely to feed package comparisons |
| Routine clean installation | Exact wheel/sdist contents and metadata, runtime dependencies only, CLI/API, bounded discovery, one complete preparation, reopening, oligos, representative rendering and browser assets | Every tutorial, method combination and comparison figure |
| Extended distribution qualification | Remaining distinct installation-sensitive workflows and exact source/package parity cases | Copies of assertions already owned by shared test cases |

Extended qualification runs for releases and changes to packaging, dependencies,
entry points, asset inclusion or verification routing. Ambiguous impact requires
extended qualification. Ordinary runtime changes retain the main suite and small
installation gate. The exact triggers must be explicit and tested before rollout.

## Ordered implementation

- [x] **1. Account for the work.** Map each current distribution command to the
  invariant it checks, its existing pytest owner and its installation-specific
  risk. Use completed logs and existing test timings first. Add start/end labels,
  elapsed time, selected scope and failure stage to the next necessary run;
  do not start another full suite just to collect a baseline. Capture quiet
  subprocess failures without dumping successful reports into the CI log.
- [x] **2. Prove one small installed workflow.** Build the actual wheel and sdist,
  install into an isolated environment with only declared runtime dependencies,
  and run from outside the checkout with import-path overrides removed. Assert
  that HOP imports from that environment. Exercise a small bounded discovery,
  one complete route, reopen/replay, CLI/API selection, exact oligo handoff and
  one figure. Check packaged browser resources and sdist example availability.
  Reuse existing requests and assertions; keep pytest and its dependencies out
  of the isolated application environment.
- [x] **3. Reuse source evidence only where it pays.** For selected exact-parity
  cases, retain the output already produced by the successful source test.
  Bind it to source-content identity, input, runtime/dependency context and
  output hashes. Isolate parallel-worker writes and retain only the required
  files in the current verification invocation. Reject absent, altered or stale
  evidence; do not silently regenerate the source example or use yesterday's
  cache. A standalone release qualification may explicitly produce its own
  reference once. If reuse adds more machinery than it saves, keep that case
  small or in extended qualification instead.
- [x] **4. Migrate checks before deleting duplicates.** Make the main tests and
  distribution checks consume shared cases/assertions. Replace script-text
  assertions with behavior and failure-propagation checks where possible;
  retain workflow/permission assertions that protect real orchestration rules.
  Map every removed command to retained evidence. Migrate one responsibility
  group at a time, then remove superseded source reruns and helper code.
- [x] **5. Wire routine and extended qualification.** Use the existing verification
  entrypoint with an explicit distribution mode. Local unknown scope defaults to
  extended; CI selects routine only for known non-packaging changes. Keep the existing
  presentation/source scope meanings. Document that the routine full gate is
  the complete source suite plus the declared installation suite, while release
  invokes extended distribution qualification. Preserve dependency audit,
  required checks, exact release-file custody and failure propagation. Split or
  group CI stages so users can see which part is running. Test all routing paths,
  including mixed, unknown and verification-file changes.
- [x] **6. Qualify once and adopt.** Run focused checks during development. Once
  the patch settles, run the main source suite once and the extended installed
  suite once, including the small cases without executing them twice. Compare
  identities, sequences, oligo chemistry and deterministic artifact bytes to
  established expectations. Use the hosted run to confirm Linux isolation,
  routing and release dependencies. Remove obsolete guidance and update
  `AGENTS.md`, the maintainer skill, performance guide and release guide together.

## Implementation and retained responsibilities

The completed hosted gate spent 3,427.79 seconds in pytest and approximately
eighteen more minutes in distribution verification. The new local command is:

```bash
uv run --locked python scripts/distribution/smoke.py \
  --out .artifacts/installation-check
```

The destination must be new. It retains distribution bytes/hashes and a short
log and elapsed time per stage; its temporary environment and molecular outputs
are removed after success or failure. Timeout/interrupt cleanup stops the process
group. The installed probe runs outside the checkout with isolated Python,
checks the actual import location and installs only declared runtime dependencies.
The existing public design example supplies the finite 64-evaluation discovery,
reopening, complete route and frozen-edition handoff. API and CLI retrieval must
match every handoff byte. One PDF/SVG, symbolic compilation and the existing
browser asset list are checked separately. Both gates use one archive inventory: all prior public sdist
requirements, exact wheel membership, and package bytes compared with source.
This is installation evidence, not visual acceptance.

On 4 November, the first check passed in 41.48 seconds with cached dependencies;
its case result matched the original 64-evaluation example exactly. An initial
eight-evaluation probe correctly failed without a complete preparation; no retry
or relaxation was introduced. Thirty-eight focused checks passed, including
import leakage, missing assets, changed handoff contents/membership, nonzero exit
and timeout. After archive-byte checks were added, the final local installation
passed in 43.95 seconds; 75 focused checks passed. Hosted timing and full
qualification remain pending.

The scientific command groups below remain in `scripts/wheel-smoke` for extended
qualification. Routine installation uses the representative case plus shared
archive checks; the main source suite still runs all its tests. The decision for
step 3 is to keep extended reference runs self-contained: caching selected pytest
outputs would add provenance and worker-coordination machinery without reducing
routine cost further. No persistent source-evidence cache was introduced.

| Existing command group | Source test owner under `tests/` | Installation responsibility / intended destination |
| --- | --- | --- |
| Build, archive inventory, public-safety scan, metadata, runtime install | `repo/test_distribution_safety.py`, `repo/test_supply_chain_contracts.py` | Shared exact inventory in both modes; metadata/safety retained |
| Documentation journey and exact/symbolic compilation | `repo/test_docs_smoke.py` | Packaged examples/CLI; representative compile in routine, remaining journey in extended |
| Public facade and producer digests | `contract/test_construction_public_facade.py` | Preserve import/identity agreement in installation checks |
| Local neighborhood, resumable collection, foldback/basal sequence populations | `contract/test_local_neighborhood_public.py`, `repo/test_construction_dogfood.py` | Exact public local results and population/member parity in extended |
| Basal junction example and candidate discovery | `repo/test_basal_junction_example.py`, `repo/test_construction_dogfood.py` | Example/rendered inventory parity in extended |
| Insert/hairpin families and continuation | `repo/test_public_scaffold_family.py` | Shared family assertions; additional installed examples in extended |
| Options, product-first discovery and terminal forms | `integration/test_construction_options.py`, `integration/test_scaffold_discovery.py`, `integration/test_terminal_scaffold.py` | Distinct workflow branches in extended |
| Five comparison cases and controlled panel | `integration/test_grouped_comparison.py`, `integration/test_comparison_loop_sequences.py`, `integration/test_stage_comparison_controls.py` | Exact comparison artifacts in extended |
| Complete journey and four compilation outcomes | `repo/test_complete_public_journey.py`, `repo/test_construction_dogfood.py` | One complete preparation in routine; additional outcomes in extended |
| Navigation and construction comparison | `integration/test_complete_construction_navigation.py`, `integration/test_construction_comparison_projection.py` | Public command/resource wiring in extended; retrieval in routine |
| Method bundles, authoring, version and CLI compilation | `integration/test_method_bundle.py`, `contract/test_linear_source_method.py` | Entry point in routine; method-bundle variants in extended |
| Molecular edit, parameter queries and envelope revision | `integration/test_molecular_edits.py`, `integration/test_parameter_exploration.py`, `integration/test_envelope_revision.py` | Saved/editable records and packaged contexts in extended |
| Browser asset checks and survey help | `repo/test_construction_dogfood.py` | Retain inexpensive resource checks in routine |
| Interface-survey continuation, replay and retrieval | `integration/test_interface_survey_public.py`, `integration/test_interface_survey_integrity.py` | Extended persistence case; routine check reopens saved discovery |
| Optional intent, figure, atlas, edition and materials | Existing `scripts/design-discovery-smoke.py`; `integration/test_design_hairpin.py`, `integration/test_design_progressive.py` | One shared case now drives the isolated probe; no duplicate implementation |

## Routing and remaining qualification

`agent-verify --distribution routine` runs the complete source gate, dependency
audit and representative isolated installation. The default extended mode runs
the full workflow parity catalog. Packaging, dependencies, CLI wiring, assets,
scripts, workflows, examples, unknown paths and manual dispatch retain extended
checks; mixed changes use the stronger mode. Routine selection covers ordinary
Python implementation/tests and Markdown guides. Missing outputs fail closed.
Release still checks the exact release wheel/sdist with the extended gate.

The extended script now labels each workflow group and reports elapsed time and
failure stage. The release build deadline is thirty minutes, correcting the old
fifteen-minute limit that was shorter than the observed distribution workload.
Routine CI retains timing/failure logs without uploading temporary environments.
The main verification deadline is four hours: the previous two-hour limit
terminated an actual full run. This is a finite failure ceiling for extended
qualification, not a runtime target or a reason to repeat successful checks.

Protected main now avoids a second full CI run after squash merge. This requires
strict up-to-date PR checks and administrator enforcement, verified through the
GitHub API before adoption. Manual dispatch remains available. No cross-run
artifact cache or trust bypass was added. The exact source and selected
distribution gate still run before merging the candidate.

Remaining: qualify this complete candidate once on hosted Linux, including the
full source suite and extended distribution gate. This CI-policy change selects
extended automatically. Confirm branch protection and the exact qualified commit
before merge. The small gate's local timing does not predict total CI duration.

## Acceptance and rollout safeguards

- Preserve the source coverage floor, molecular validation and existing failure
  semantics. A timeout, skipped stage or empty case selection cannot pass.
- Test corrupted or mismatched parity evidence and failure propagation through
  the runner and required CI context. Keep source and installed execution
  independent even when they share assertions and inputs.
- Compare exact molecular identities, sequences, chemistry and deterministic
  artifacts; file existence alone is insufficient. Keep visual regression
  responsibilities in the presentation tests.
- Aim for a routine installed check of at most five minutes on the normal CI
  runner. This is a performance target to measure, not an established result or
  permission to drop required checks. Record cold and cached timings, peak memory,
  source rerun count and installation-suite time separately from total CI time.
- Adopt only after each removed command has a retained owner and the hosted gate
  passes. Do not reduce a required check to get an already-running PR merged.
  Preserve extended qualification as the recovery route if the smaller suite
  misses an installation defect; add a focused regression for the actual gap.

After acceptance, retain this mapping and decisions in the owning verification
guide and retire the completed checklist rather than keeping competing policies.
