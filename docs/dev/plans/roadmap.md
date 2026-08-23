---
doc_id: hop-roadmap
title: HOP Design implementation and migration roadmap
intent: Define phased deliverables, gates, rollback, and proof of done.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
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

Status: standalone mechanics and bounded placement, precursor, and cross-agent
released-foldback discovery implemented; live predecessor differential parity
closed and released in `v0.1.0a6`.

Define precursor, nick, release/exposure, retained tract, turn, foldback arm,
pair map, bounded search, and stable rejection codes. Port behavior against
sanitized accepted, rejected, near-match, and truncated parity fixtures. The
predecessor remains authoritative only for behavior outside the supported,
parity-closed surface.

Available: exact evaluation including explicit cap-only zero-pair junctions,
pair/run measurements, `HOP-FOLD-001`
through `HOP-FOLD-007`, exact-first bounded search, truthful completion status,
and sanitized public fixtures. The live differential gate records exact
candidate equality, bounded-subset near-hit parity, and the intentional
caller-policy ordering difference.

Target-search parity includes bounded discovery across caller-supplied
processing-agent placements and hairpin geometry. Catalog scanning and
compilation of already-selected options do not, by themselves, satisfy that
discovery contract.

Available discovery now covers exact and nearest nicking-site placement for a
declared nick strand, boundary, paired tract, and turn allowance. A separate
bounded operation constructs exact precursor sequences only inside
caller-authored IUPAC domains, derives the returning arm, reports additional
nick sites, and distinguishes template conflict, candidate rejection, node
truncation, and returned-hit truncation. Sanitized sequence and neutral-order
parity now matches the predecessor's physical candidate while excluding its
vendor and application rank. Cross-agent geometry discovery now evaluates both
agent catalogs, both release orientations, and an exact-first nick-boundary
window together. It returns correlated physical domains and cardinality without
choosing a precursor. The separate precursor search now intersects one selected
geometry with a complete caller-authored IUPAC template, counts correlated pair
domains correctly, and returns bounded content-addressed exact sequences. A
later bounded join now projects each exact precursor and pairs it with a basal
route only when the same molecular strand remains active and survives terminal
nicking. A live-catalog differential comparison now matches five exact
candidate identities, active sequences, coordinate lineage, and routed
foldback views. The predecessor's 64 returned near hits are a verified subset
of HOP's 130 neutral near geometries; its reported pre-truncation count is 118.
That bounded-list difference is explicit rather than treated as equality.
Predecessor ordering and warning/vendor filters remain caller policy, while HOP
keeps neutral physical order. Complete partner-strand separation remains an
independent stricter constraint and excludes two otherwise valid
downstream-site placements.

The initial placement and precursor-discovery API shipped in `v0.1.0a1`. The
protected release repeated the Phase 7 artifact gate, and the first private
comparison path installs a versioned wheel rather than a sibling checkout. The
cross-agent geometry, exact-precursor, hairpin-junction route schemas,
route-owned view projection, and origin-boundary released-state correction were
released in `v0.1.0a6`.

## Phase 3: basal mechanics

Status: standalone mechanics, bounded arm-pair enumeration, bounded
enzyme-compatible geometry, bounded basal route composition, and live routed
differential parity closed and released in `v0.1.0a6`.

Define arm ordering, pair classes, site order, strand roles, terminal-nick
geometry, deterministic ranking, and caller-supplied constraint profiles.
Separate physical invariants from selection policy. Application thresholds are
never built-in defaults.

Available: S3/S2/S1/S0 physical pair calls, explicit G:T wobble choice,
M/W/X interoperability profiles, caller-owned active/reserve/reject policy,
literal nicked/surviving strands, explicit reserve acceptance, and bounded
candidate enumeration inside caller-authored IUPAC arm domains. A sanitized
16-pair differential fixture reproduces six predecessor active candidates,
nine reserve outcomes, and one explicit rejection. HOP uses canonical physical
record order and deliberately omits predecessor profile-bucket, control,
mismatch-tier, vendor, and procurement rank. Agent-compatible basal geometry
now uses a separate signed-coordinate search with explicit retained-scar and
post-nick domains. It contains no hidden fully-degenerate downstream rule.
The basal route join now connects each exact candidate's left arm to the
retained scar, rejects a retained release site, derives terminal strand roles,
and propagates both upstream searches' truncation evidence. It returns neutral
compatible routes rather than a preferred enzyme. The hairpin-junction join
preserves end-specific release agents and requires strand continuity. A route
candidate now replays its embedded exact precursor against its selected
geometry before a route-owned view can be built. Live exact identity, released
state, lineage, and normalized view comparisons pass; ranking and catalog
warning policy remain deliberately downstream.

## Phase 4: complete plans and bundles

Status: resolved mechanics, bounded design-space planning, design bundles, and
method bundles implemented; default downstream adoption remains open.

Resolve physical routes, source oligos, processing steps, expected strand
states and intermediates, hairpin-encoding sequences, route-required primers/adapters, and
complete provenance. Add explicit enumeration statuses and hard budgets.

Available: foldback, payload, derived paired arm, basal composition, optional
variable-length paired stem extensions with literal noncanonical pairs;
route-neutral component assembly for caller-supplied or inherited components;
resolved release state; exact feature spans; verified content-addressed design
bundles; and renderer-free Cartesian design-space planning with pre-allocation
cardinality checks. The
`linear-source-multinick-size-selection-hairpin-pcr@1` compiler now resolves six
materials, complete site multiplicity, all denatured fragments, length
selection, adapter pairing, two ligations, a hairpin-PCR duplex, and a
destination-neutral facing restriction product for caller-supplied
sequences and agents. Its strict request, result, and plan reject cross-state
serialized drift.

The method compiler resolves exact molecules. A bounded symbolic pool
assessment remains open; design-level IUPAC support is not evidence that every
member of a degenerate pool follows one exact physical trajectory.

The compiled one-dimensional design product remains `HairpinEncodingInsert`.
`HairpinPcrDuplex` is a separate physical method state, and
`RestrictionDigestProduct` is its destination-neutral projection. Complete
method requests now produce a separate replay-verified `MethodBundle` with the
strict request and plan, an eight-state trajectory, duplex and
restriction-product FASTA, deterministic GenBank, and the exact
hairpin-encoding projection. The design bundle remains unchanged. Open work is
the default downstream consumer cutover and its hosted validation. Selective
batch bundle orchestration remains separate.

A primer or adapter is a process material, not a molecular intermediate. HOP
owns a vendor-neutral material only when the declared generic route requires it;
application context and procurement metadata remain caller-owned.

The implemented method boundary is narrower than a general reaction simulator.
It explains one linear-source multi-nick path through typed molecular states
and events. Reaction conditions, controls, execution, and larger construct
placement remain caller-owned. See the
[processing method boundary](../../processing-method-boundary.md).

## Phase 5: view contracts and optional plots

Status: typed contracts and deterministic SVG implemented.

Add typed foldback, released-product, and basal view models. Renderers consume
those models and cannot recompute molecular state. Plot dependencies remain an
optional extra.

The current renderer is dependency-free SVG. Additional PNG/PDF renderers and
secondary-structure predictors are optional artifact consumers, not a second
scientific model. They link results to a plan or bundle digest and cannot
silently change compile validity. A general plugin protocol remains deferred
until more than one independent integration establishes a stable seam.

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

Status: implemented; required for every prerelease.

Create a protected-main tag and GitHub release only after Phase 6 hosted checks
pass. The GitHub release workflow must produce a clean wheel and sdist,
verify the exact files before publication, publish SHA-256 checksums, confirm
main ancestry, and create the Release with those files without PyPI credentials.
This versioned artifact is the first permanent downstream dependency candidate.

Evidence for each published prerelease must show that the protected-main tag
triggered the build-and-publish workflow; the
exact wheel and sdist passed the distribution smoke before publication; the
Release includes `SHA256SUMS`; and a separate public download reproduced the
checksums, clean-wheel install, metadata checks, and source/wheel bundle parity.
See the [release history](https://github.com/e-south/hop-design/releases).

## Phase 8: downstream consumer and dogfood

Status: the typed product and method boundaries shipped by `v0.1.0a5`; the
`v0.1.0a6` released pin, one application consumer, atomic composition handoff,
advisory structure assessment, and a second lineage replay are locally proven.
Required hosted checks for the downstream change have not executed, so merge
and default adoption remain open.

Add a shadow adapter in the application-owning repository through HOP's public
API. Establish zero predecessor imports in the migrated path, artifact parity,
exact sequence/span equality, and a representative private workflow. The
caller owns larger construct placement and application semantics. A generic
intermediate-repository adapter is added only if a second independent consumer
proves that boundary reusable.

Entry precondition: the consumer must install the Phase 7 versioned HOP artifact
through an authorized reproducible channel. An editable sibling-path override
is useful for an ephemeral local probe but is not an accepted adapter or CI
dependency. PyPI is optional; a pinned GitHub release artifact satisfies this
gate.

Historical or inherited records may use `component_assembly` with caller-owned
lineage references. Absence of a selected process route does not make their
molecular composition infeasible. Route parity is required only where the
application asserts a route.

The verified `HairpinEncodingInsert`, rather than a caller's legacy domain
compiler, authors the hairpin-specific segment order and spans. An application
may add its context around that object. A generic composition, assessment, or
rendering service may consume the result without rederiving HOP features. HOP
supersedes the hairpin-specific authoring layer, not reusable larger-placement
or assessment services.

## Phase 9: cutover and deduplication

Status: upstream predecessor removal implemented; the downstream protected-main
cutover remains open and the cross-repository state is not yet coherent.

Parity-closed HOP-owned predecessor producers have been removed from their
protected upstream main branch. That does not close the ecosystem migration:
the pending downstream consumer must still pass its required hosted checks,
adopt the released HOP artifact by default, and close the final import audit.
The intended cutover-before-removal order was not preserved across protected
branches. Do not hide that mismatch with a compatibility shim; close it by
validating and merging the prepared downstream cutover.

For every remaining or future predecessor surface, switch consumers through a
reversible default, execute the declared representative cases, then remove only
superseded HOP-owned code. Do not retain a permanent compatibility shim or
run-directory reader. Workspace routing changes only after the new ownership
and downstream paths are real. The caller-owned cutover record must name the
responsible maintainer, compared versions and outputs,
zero-unexplained-mismatch rule, rollback trigger, rollback mechanism,
consumer-import audit, and evidence used to close the gate. Elapsed time is not
evidence and is not a closure requirement.

## Product done

- A clean machine can install the wheel and reproduce exact and symbolic demos.
- Spec, plan, bundle, diagnostics, coordinates, catalogs, and limits have stable
  strict schemas and negative tests.
- Bundles verify and downstream consumers can load their complete typed content
  only after deterministic replay.
- Product names distinguish a one-dimensional hairpin encoding from a physical
  PCR duplex and a destination-specific assembly fragment.
- Docs, CLI, Python API, skills, and CI exercise the same use cases.
- The package contains no private data or caller-repository runtime dependency.

## Ecosystem migration done

- Sanitized differential fixtures establish accepted/rejected candidates, ordering,
  diagnostics, spans, sequences, and artifacts.
- Every protected downstream workflow uses only the public HOP API and no
  removed predecessor import remains.
- Future predecessor removal occurs only after its cutover evidence gate, with
  no duplicate scientific authority remaining.
