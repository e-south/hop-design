---
doc_id: hop-python-api
title: HOP Design Python API
intent: Document the stable public Python facade and its failure contracts.
audience:
  - Python users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: reference
---

# Python API

The package root is the design-language golden path. Three sibling facades
make specialized competency questions explicit:

```python
import hop_design as hop
import hop_design.discovery as discovery
import hop_design.methods as methods
import hop_design.views as views
```

Use `hop` for design compilation, payloads, bounded design spaces, and explicit
component evaluation. Use `discovery` for bounded catalog queries, `methods`
for named production methods and molecular states, and `views` for projections
and rendering. Internal `hop_design.design.*` modules are not public facades.

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

Foldback, basal, and release operations accept explicit typed requests. Basal
pair classification is physical; active/reserve/reject classification comes
from the caller-supplied `BasalConstraintProfile`. See the
[mechanics reference](mechanics-api.md).
Explicit foldback evaluation can represent a cap-only junction with zero
retained and returning paired bases. Foldback-arm search remains limited to a
nonempty retained tract.

Precursor search is a second bounded operation after placement discovery. The
request names one exact placement and supplies IUPAC domains for the precursor
and any required turn extension. Motif constraints are intersected with those
domains before enumeration. Incompatible domains return `HOP-CAND-001`;
caller-prohibited additional nick sites return `HOP-CAND-002`. Node and result
truncation are separate and explicit.

Basal candidate search takes two explicit four-nucleotide IUPAC arm templates.
It calculates the exact Cartesian cardinality before evaluation, classifies
each exact pair through the supplied `BasalConstraintProfile`, and returns
active candidates or active plus reserve candidates according to `acceptance`.
Every examined non-hit is accounted for by policy status and reason. Returned
order uses literal left arm, right arm, and content identity. Compact M/W/X
profiles remain physical annotations and policy inputs; they do not determine
which candidates survive a hit budget. `max_search_nodes` and `max_hits`
produce separate truncation evidence.

Basal processing-geometry search is a separate operation. It normalizes a
selected release geometry to a signed top-cut origin, evaluates exact terminal
nick placement for each bounded catalog entry, intersects caller-authored scar
and post-nick domains, and reports complete per-agent feasibility. The
`compatible` post-nick mode permits an explicit nonempty narrowing;
`preserve` requires the authored domain to remain unchanged. Request, limit,
and result models are available from `hop_design.discovery`.

Basal processing-route search is the bounded join of those two explicit result
sets. It uses the basal left arm as the retained scar, rejects domain conflicts
and a retained release motif, and derives the terminal nick and surviving
strand. It returns all compatible joins within the caller budgets in neutral
upstream order. Upstream incompleteness and local node or hit truncation remain
distinct; this operation does not select an enzyme or establish
released-foldback continuity.

Released-foldback geometry search evaluates the bounded cross-product of
nicking agents, release agents, release orientations, and exact-first nick
boundaries. Each examined row records process footprints, strand-specific cuts,
foldback pair domains, minimum precursor extent, and exact compatible-sequence
cardinality. Downstream-site placement and complete two-strand separation are
independent request constraints. The search does not choose one sequence or
apply catalog warnings, vendor status, or application preference. Node and returned-
hit truncation are independent.

Released-foldback precursor search consumes one selected geometry and one
same-length caller-authored IUPAC template. It intersects all sequence and
correlated pairing domains before enumeration, returns content-addressed exact
precursors with contiguous `canonical_ordinal`, and reports `caller_domain_conflict`
when the intersection is empty. Node and hit truncation are independent. The
specialized request, limits, candidate, and result models are available from
`hop_design.discovery`.

Hairpin-junction route search consumes exact released-foldback precursor and
basal-route results. It projects the released state and returns only pairs for
which the released active strand is also the basal surviving strand. It does
not require matching release-agent identities at the two ends or apply caller
selection policy. Its specialized limits and result models are available from
`hop_design.discovery`.

The `hop_design.views` facade provides
`build_released_foldback_precursor_view(...) -> WorkflowView` and
`build_hairpin_junction_route_view(route) -> WorkflowView`. Both derive the
released and foldback panels from exact discovery results and are not
package-root exports.

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
