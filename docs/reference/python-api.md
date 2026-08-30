---
doc_id: hop-python-api
title: HOP Design Python API
intent: Document the stable public Python facade and its failure contracts.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: reference
---

# Python API

The package root is the single-design language. Five sibling facades make
scientist workflow and specialized competency questions explicit:

```python
import hop_design as hop
import hop_design.construction as construction
import hop_design.discovery as discovery
import hop_design.methods as methods
import hop_design.spaces as spaces
import hop_design.views as views
```

Use `hop` for design compilation, payloads, bounded design spaces, and explicit
component evaluation. Use `construction` for file-oriented payload-centered
construction compilation and its neutral projections, `discovery` for bounded
catalog queries, `methods` for named production methods and molecular states,
`spaces` for the minimal scientist-facing substrate-space journey, and `views`
for state projections and rendering. Internal `hop_design.design.*` modules are
not public facades.

## Payload-centered construction

All operations and receipts in this section use `hop_design.construction`.

- `compile_construction(source_path, design_bundle_path=...) -> ConstructionCompilation`
  loads one strict file and a separate verified design authority, discovers
  local neighborhoods, composes the bounded whole route, and returns an opaque
  write-capable receipt.
- `discover_source_partition(source_path) -> SourcePartitionDiscovery`
  enumerates canonical nonempty subsets of provisioned strand-exposure
  nickases, applies every actionable site, derives all denatured fragments,
  applies the declared length selection, and accepts only exact required
  survivor spans. The opaque receipt exposes exact search accounting and
  deterministic JSON/CSV bytes.
- `load_verified_source_partition(result_path) -> SourcePartitionDiscovery`
  safely reopens canonical result JSON and repeats molecular, candidate-space,
  completion, and identity replay before returning the same opaque receipt.
- `load_verified_construction_bundle(path) -> VerifiedConstructionBundle`
  checks portable bytes and semantically replays the embedded design, local
  authorities, complete result, and root manifest.
- `project_foldback_feasibility(receipt) -> ConstructionProjection`
- `project_basal_feasibility(receipt) -> ConstructionProjection`
- `project_relaxation_frontier(receipt, family=...) -> ConstructionProjection`
- `project_complete_construction_summary(receipt) -> ConstructionProjection`
- `project_construction_trajectory(receipt, materialized_realization_id=...) -> ConstructionProjection`

The source document cannot author design or result identities. Receipts expose
bundle, result, and design-bundle identity; endpoint and status; accepted,
examined, and nominal counts; and accepted materialized-realization identities
rather than internal result models. `ConstructionCompilation.write(path)`
atomically persists the portable authority. Projection
packets provide canonical JSON, tidy CSV when defined, and SVG bytes; writing a
packet is atomic and create-only. A trajectory always requires an explicit
accepted realization identity.

These operations establish only deterministic digital discovery,
materialization, composition, verification, and projection. They do not
establish laboratory construction, destination compatibility, QC, activity,
yield, or an optimized route.

Source partitioning is not basal discovery. Its nick functions distinguish a
retained-fragment boundary from excluded-fragment cleanup. Canonical enzyme
subset order is replay metadata, not rank. PCR handles and primer
thermodynamics are outside this local search.

See the [construction guide](../guides/compile-construction.md), the
[source-partition guide](../guides/discover-source-partitions.md),
[construction-bundle layout](construction-bundle-layout.md), and
[construction projection contracts](view-contracts.md#complete-construction-projections).

## Substrate spaces and design sets

All operations and public contracts in this section use `hop_design.spaces`.

- `preview_space(spec) -> SubstrateSpacePreview` validates one segmented
  authored arm, derives its paired arm, computes exact cardinality, and returns
  `ready`, `blocked`, or `invalid` without enumerating or writing.
- `compile_space(spec, destination=...) -> VerifiedHairpinDesignSet` expands a
  ready space exhaustively, compiles unchanged member `HopBundle` authorities,
  verifies the complete collection, generates review projections, and commits
  one new destination atomically.
- `load_verified_design_set(path) -> VerifiedHairpinDesignSet` verifies the
  collection inventory and identity, replays canonical enumeration, and loads
  every unique member through the existing semantic bundle verifier.

The exact facade allowlist also exposes `SubstrateSpaceSpec`,
`SubstrateSpacePreview`, `HairpinDesignSet`, and
`VerifiedHairpinDesignSet`. These names are not package-root re-exports.
`context` is descriptive review metadata and is excluded from collection
identity. V1 compilation is exhaustive or blocked; it never returns a
truncated authoritative set.

Success establishes complete digital design derivation. It does not establish
a named construction method, destination compatibility, physical
construction, QC, or biological activity. See the
[design-set layout](design-set-layout.md) and
[substrate-space guide](../guides/substrate-spaces.md).

## Compile and integrity

- `create_spec(sequence=..., design_id=...) -> HopSpec` expands the named,
  versioned generic default into explicit references.
- `load_spec(path) -> HopSpec | ResolvedHopSpec` safely loads strict JSON/YAML
  by exact schema ID under a byte limit and rejects symlinks.
- `check(spec) -> CheckReport` aggregates expected feasibility diagnostics and
  raises for corrupt configuration.
- `compile(spec)` compiles one explicit spec.
- `compile(sequence=..., design_id=...)` is the observationally equivalent
  convenience path.
- `Compilation.write(path)` verifies and atomically writes a new bundle path;
  it refuses to replace an existing path.
- `verify_bundle(path)` validates safe paths, complete inventory, digests, root
  identities, strict spec/plan/provenance schemas, cross-artifact references,
  plan-derived FASTA, absence of unmanifested files, and a complete deterministic
  replay of the spec into the stored plan, artifacts, and manifest.
- `load_verified_bundle(path) -> VerifiedHopBundle` returns the strict semantic
  contents only after the same verification and replay succeed.

Provide exactly one of `spec` or `sequence`. `design_id` is only valid with
`sequence`. Expected infeasibility raises `InfeasibleDesignError` at compile;
invalid call shapes raise `TypeError`; corrupt bundles raise
`BundleIntegrityError`.

A `ResolvedHopSpec` compiles supplied foldback and basal components through an
explicit design derivation. The resulting bundle makes no claim that HOP
discovered those components or that an enzyme route exists. A release
projection requires explicit terminal-nick geometry, but still does not create
a temporal method history.
An optional `PairedStemExtensionRequest` records variable non-payload paired
context between the basal junction and payload stem.

## Payload records and variants

- `collect_payloads(records, duplicate_policy=...) -> PayloadCollection`
  consumes any iterable and records explicit `fail`, `dedupe`, or `keep`
  behavior for duplicate sequences. Duplicate record IDs always fail.
- `load_fasta_payloads(path) -> tuple[PayloadRecord, ...]` and
  `load_csv_payloads(path, id_column=..., sequence_column=...)` create the same
  strict records as inline input under explicit byte, record, and total-nt
  limits.
- `expand_payload(record, max_variants=...) -> PayloadExpansionResult` computes
  exact cardinality before allocation and raises `VariantBudgetExceededError`
  instead of truncating.
- `plan_design_space(space) -> DesignSpacePlan` computes Cartesian cardinality
  before row allocation, then returns one checked `ResolvedHopSpec` per bounded
  payload/foldback/basal/release combination without rendering bundles. Its
  explicit duplicate-final-sequence policy is `FAIL` or `KEEP`; it never drops
  combinations silently.

## Physical mechanics

Component evaluation and released-state projection use the design-language
root. Every `search_*` operation and its request, limit, and result contracts
use `hop_design.discovery`.

- `evaluate_foldback(request) -> FoldbackEvaluation`
- `search_foldback_arms(request, limits=...) -> FoldbackSearchResult`
- `evaluate_basal_pairing(request, constraints=...) -> BasalEvaluation`
- `search_basal_candidates(request, limits=...) -> BasalCandidateSearchResult`
- `search_basal_processing_geometries(catalog=..., request=..., limits=...) -> BasalProcessingGeometrySearchResult`
- `search_basal_processing_routes(basal_candidates=..., processing_geometries=..., limits=...) -> BasalProcessingRouteSearchResult`
- `search_released_foldback_geometries(catalog=..., request=..., limits=...) -> ReleasedFoldbackGeometrySearchResult`
- `search_released_foldback_precursors(request, limits=...) -> ReleasedFoldbackPrecursorSearchResult`
- `search_hairpin_junction_routes(released_precursors=..., basal_routes=..., limits=...) -> HairpinJunctionRouteSearchResult`
- `evaluate_paired_stem_extension(request) -> PairedStemExtension`
- `project_released_strand_state(request) -> ReleaseProjectionResult`
- `classify_motif_presence(sequence=..., motif=...) -> MotifPresenceReport`
- `scan_nicking_agent(sequence, agent=...) -> tuple[ResolvedNickSite, ...]`
- `scan_release_agent(sequence, agent=...) -> tuple[ResolvedReleaseSite, ...]`
- `search_nicking_placements(catalog=..., target=..., limits=...) -> NickingPlacementSearchResult`
- `search_foldback_precursors(request, limits=...) -> FoldbackPrecursorSearchResult`

The operation list is the signature index, not the semantic authority. Follow
the reference that matches the question:

- [component evaluation](component-evaluation.md) for foldback, basal, paired
  stem, released-strand projection, and compiler integration;
- [processing discovery](processing-discovery.md) for nick placement, exact
  precursor sequence, basal candidates, and terminal processing routes;
- [released-foldback routes](released-foldback-routes.md) for joint geometry,
  exact selected precursors, and active/surviving-strand continuity; and
- [workflow views](view-contracts.md) for renderer-independent projections.

Every bounded search requires explicit node and hit limits. Its status,
canonical order, physical measurements, caller selection, and downstream use
remain distinct claims.

## Linear-source method

All operations and public contracts in this section use `hop_design.methods`.

- `list_method_capabilities() -> tuple[MethodCapability, ...]`
- `resolve_linear_source_hairpin_pcr_materials(spec) -> LinearSourceHairpinPcrMaterialsPlan`
- `compile_linear_source_multinick_hairpin_pcr(request) -> LinearSourceMultinickHairpinPcrResult`
- `compile_linear_source_method_bundle(request) -> MethodCompilation`
- `load_verified_method_bundle(path) -> VerifiedMethodBundle`
- `verify_method_bundle(path) -> MethodBundle`

The capability query reports every named `MethodKind` in deterministic order,
with implementation availability and the exactness accepted by that method's
input contract. `exact_only` means callers must supply exact sequences;
`not_defined` means the unavailable method has no public request schema. The
query does not select a method, construct a request, or resolve one.

The material input records six sequence materials and whether ligatable 5′
phosphates are supplied or produced by a kinase step. The resolver checks
terminal primer binding. The bounded method compiler then resolves every nick,
fragment, selected strand, pair, bond, PCR boundary, facing restriction
product, and exact cohesive end. Expected infeasibility returns a `MethodOutcome`; corrupt contracts
raise validation errors. See the
[linear-source material reference](linear-source-method-materials.md) and
[method boundary](../methods/destination-neutrality.md). A complete request can be
written as a replay-verified method bundle containing the plan, trajectory,
FASTA, GenBank, and hairpin-encoding projection. Infeasible resolution raises
`MethodResolutionError` only when the caller requests that complete artifact
boundary; the lower-level compiler continues to return its typed outcome.

## Views

All operations and public contracts in this section use `hop_design.views`.

- `build_foldback_view(evaluation) -> WorkflowView`
- `build_foldback_junction_view(evaluation) -> WorkflowView`
- `build_released_workflow_view(state, foldback) -> WorkflowView`
- `build_basal_pairing_view(evaluation) -> WorkflowView`
- `build_basal_view(evaluation, nicked_strand=...) -> WorkflowView`
- `build_method_trajectory_view(plan) -> WorkflowView`
- `render_workflow_svg(view) -> bytes`

The renderer consumes the typed view and performs no molecular derivation.
The same `hop_design.views` surface provides
`build_hairpin_junction_route_view(...)` and
`build_released_foldback_precursor_view(...)`; they are not package-root
exports.

Stable package-root types cover payloads, design specs, coordinates, junctions,
processing agents, design results, and operator-facing errors. Discovery,
method, molecular-state, and view contracts live only on their named sibling
facades; the root does not forward them.
