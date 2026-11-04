---
doc_id: hop-verification-cost-plan
title: Remove duplicate verification work
intent: Preserve scientific and installation checks while reducing repeated discovery and rendering in CI.
audience: [maintainers, agent executors]
owner: HOP Design maintainers
status: active
last_verified: 2026-11-04
doc_type: explanation
journey: [maintain]
---

# Remove duplicate verification work

Status: planned; no verification runner changes are implemented by this plan.

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
Do not cancel, restart or change the gate already running to adopt this plan.

The local Python-matrix and README/artwork policy is a separate, not-yet-hosted
change. Reconcile with it before promotion; this plan does not imply that either
policy is already deployed.

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

- [ ] **1. Account for the work.** Map each current distribution command to the
  invariant it checks, its existing pytest owner and its installation-specific
  risk. Use completed logs and existing test timings first. Add start/end labels,
  elapsed time, selected scope and failure stage to the next necessary run;
  do not start another full suite just to collect a baseline. Capture quiet
  subprocess failures without dumping successful reports into the CI log.
- [ ] **2. Prove one small installed workflow.** Build the actual wheel and sdist,
  install into an isolated environment with only declared runtime dependencies,
  and run from outside the checkout with import-path overrides removed. Assert
  that HOP imports from that environment. Exercise a small bounded discovery,
  one complete route, reopen/replay, CLI/API selection, exact oligo handoff and
  one figure. Check packaged browser resources and sdist example availability.
  Reuse existing requests and assertions; keep pytest and its dependencies out
  of the isolated application environment.
- [ ] **3. Reuse source evidence only where it pays.** For selected exact-parity
  cases, retain the output already produced by the successful source test.
  Bind it to source-content identity, input, runtime/dependency context and
  output hashes. Isolate parallel-worker writes and retain only the required
  files in the current verification invocation. Reject absent, altered or stale
  evidence; do not silently regenerate the source example or use yesterday's
  cache. A standalone release qualification may explicitly produce its own
  reference once. If reuse adds more machinery than it saves, keep that case
  small or in extended qualification instead.
- [ ] **4. Migrate checks before deleting duplicates.** Make the main tests and
  distribution checks consume shared cases/assertions. Replace script-text
  assertions with behavior and failure-propagation checks where possible;
  retain workflow/permission assertions that protect real orchestration rules.
  Map every removed command to retained evidence. Migrate one responsibility
  group at a time, then remove superseded source reruns and helper code.
- [ ] **5. Wire routine and extended qualification.** Use one distribution
  runner with a small default and an explicit extended mode. Keep the existing
  presentation/source scope meanings. Document that the routine full gate is
  the complete source suite plus the declared installation suite, while release
  invokes extended distribution qualification. Preserve dependency audit,
  required checks, exact release-file custody and failure propagation. Split or
  group CI stages so users can see which part is running. Test all routing paths,
  including mixed, unknown and verification-file changes.
- [ ] **6. Qualify once and adopt.** Run focused checks during development. Once
  the patch settles, run the main source suite once and the extended installed
  suite once, including the small cases without executing them twice. Compare
  identities, sequences, oligo chemistry and deterministic artifact bytes to
  established expectations. Use the hosted run to confirm Linux isolation,
  routing and release dependencies. Remove obsolete guidance and update
  `AGENTS.md`, the maintainer skill, performance guide and release guide together.

## Next-slice contract

Implement steps 1 and 2 on the existing local CI/banner branch after reconciling
the source base. Produce the responsibility map and a representative isolated
installation check using the existing test owners. Keep the old gate callable
and its CI routing unchanged during this slice; the new check is qualified
explicitly, not appended permanently to an already expensive routine gate.

Done means the installed check passes, emits useful timing/failure information,
and demonstrates that missing assets, an import from the checkout, altered
handoff data and a failed subprocess are rejected. Report selected test cases,
runtime, isolation evidence and remaining unmapped checks. No remote launch or
release action belongs to this slice. No user decision is blocking it.

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
