---
doc_id: hop-roadmap
title: HOP Design implementation and migration roadmap
intent: Define phased deliverables, gates, rollback, and proof of done.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# HOP Design implementation and migration roadmap

## Outcome

Ship a public-by-construction compiler for exact and symbolic payloads, then
migrate only HOP-owned molecular behavior from predecessor implementations.
Downstream consumers switch after parity; duplication is removed only after
real workflow proof. No public route may embed private application data.

## Phase 1: standalone package foundation

Status: implemented in the initial bootstrap.

Deliver a locked package, CI configuration, contracts, exact and symbolic demonstrations,
Python API, CLI, JSON/FASTA bundle, repository docs, skills, and deterministic
verification. Exit when source and clean-wheel installs produce the same bundle
digest and negative tests cover unknown fields, stale schemas, implicit
expansion, invalid alphabets, corrupt bundles, and unsafe paths.

## Phase 2: foldback mechanics

Status: standalone mechanics implemented; predecessor differential parity open.

Define precursor, nick, release/exposure, retained tract, turn, foldback arm,
pair map, bounded search, and stable rejection codes. Port behavior against
sanitized accepted, rejected, near-match, and truncated parity fixtures. The
predecessor remains authoritative until semantic equality passes.

Available: exact evaluation, pair/run measurements, `HOP-FOLD-001`
through `HOP-FOLD-007`, exact-first bounded search, truthful completion status,
and sanitized public fixtures. Open gate: differential accepted/rejected set,
ordering, and target-search parity against the predecessor.

## Phase 3: basal mechanics

Status: standalone mechanics implemented; predecessor candidate/ranking parity open.

Define arm ordering, pair classes, site order, strand roles, terminal-nick
geometry, deterministic ranking, and caller-supplied constraint profiles.
Separate physical invariants from selection policy. Application thresholds are
never built-in defaults.

Available: S3/S2/S1/S0 physical pair calls, explicit G:T wobble choice,
M/W/X interoperability profiles, caller-owned active/reserve/reject policy,
literal nicked/surviving strands, and explicit reserve acceptance. Open gate:
differential candidate-set, geometry, and ordering parity.

## Phase 4: complete plans and bundles

Status: resolved-mechanics and bounded design-space planning implemented; full build outputs open.

Resolve physical routes, source oligos, processing steps, expected strand
states and intermediates, final inserts, primers/adapters where required, and
complete provenance. Add explicit enumeration statuses and hard budgets.

Available: foldback, payload, derived paired arm, basal composition; resolved
route state graph; optional released state; exact feature spans; expected
intermediates; verified content-addressed bundles; and renderer-free Cartesian
design-space planning with pre-allocation cardinality checks. Open work includes
selective batch bundle orchestration and any route that genuinely requires
primers/adapters rather than synthetic placeholders.

## Phase 5: view contracts and optional plots

Status: typed contracts and deterministic SVG implemented.

Add typed foldback, released-product, and basal view models. Renderers consume
those models and cannot recompute molecular state. Plot dependencies remain an
optional extra.

The current renderer is dependency-free SVG. Additional PNG/PDF renderers are
optional consumers, not a second scientific model.

## Phase 6: public repository hardening

Status: implemented; public governance and hosted evidence verified.

Complete file-based specs, FASTA/CSV sources, design spaces, schema and CLI
snapshots, held-out agent-operation evaluations, install/build matrices, and
release documentation. Remove the publication brake only in an authorized
release change.

Available: byte-bounded strict JSON/YAML design loading, bounded typed
iterable/FASTA/CSV payload sources, explicit symbolic expansion, typed design
spaces, root-facade mechanics and integrity operations, schema/docs surfaces,
the source/wheel harness, public GitHub repository, protected main branch,
restricted SHA-pinned Actions policy, Python 3.12/3.13/3.14 jobs, dependency
review, committed CodeQL workflow, security controls, and a GitHub-release
artifact workflow. Hosted pull-request evidence has exercised all required
contexts under the enforced branch rule.

PyPI is not part of this phase. The publication brake remains active. A future
PyPI gate requires its own trusted-publisher and protected-environment review.

## Phase 7: versioned GitHub artifact

Status: not started.

Create a protected-main tag and GitHub release only after Phase 6 hosted checks
pass. The GitHub release workflow must produce a clean wheel and sdist,
verify the exact files before publication, publish SHA-256 checksums, confirm
main ancestry, and create the Release with those files without PyPI credentials.
This versioned artifact is the first permanent downstream dependency candidate.

## Phase 8: downstream adapter and dogfood

Status: not started.

Add thin adapters in caller-owned repositories through HOP's public API. Establish
zero predecessor imports, artifact parity, exact sequence/span equality, and a
representative private workflow. Adapters own larger construct placement and
application semantics.

Entry precondition: the consumer must install the Phase 7 versioned HOP artifact
through an authorized reproducible channel. An editable sibling-path override
is useful for an ephemeral local probe but is not an accepted adapter or CI
dependency. PyPI is optional; a pinned GitHub release artifact satisfies this
gate.

## Phase 9: cutover and deduplication

Status: not started.

Switch consumers, observe the migration window, then remove only superseded
HOP-owned predecessor code. Do not retain a permanent compatibility shim or
run-directory reader. Workspace routing changes only after the new ownership
and downstream paths are real. The caller-owned observation record must name
the responsible maintainer, minimum elapsed time and representative-run count,
compared outputs, zero-unexplained-mismatch rule, rollback trigger, rollback
mechanism, and evidence used to close the gate.

## Product done

- A clean machine can install the wheel and reproduce exact and symbolic demos.
- Spec, plan, bundle, diagnostics, coordinates, catalogs, and limits have stable
  strict schemas and negative tests.
- Bundles verify and all scientific artifacts derive from one plan.
- Docs, CLI, Python API, skills, and CI exercise the same use cases.
- The package contains no private data or caller-repository runtime dependency.

## Ecosystem migration done

- Sanitized differential fixtures establish accepted/rejected candidates, ordering,
  diagnostics, spans, sequences, and artifacts.
- Real downstream workflows use only the public HOP API.
- Superseded code is removed after the observation gate, with no duplicate
  scientific authority remaining.
