# Compile sequence anatomy and named methods

Use the package root, `hop_design`, for a single design specification, payload
records and component evaluation. Use the named `discovery`, `methods` and
`views` facades for bounded processing searches, complete production methods,
and molecular drawings.

For complete preparation discovery, use the [discovery reference](discovery.md).
Return to the [Python API task index](../python-api.md) for other operations.

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
explicit design derivation. A release projection requires explicit terminal-nick
geometry. Construction programs and named methods record their respective
molecular-state histories.
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

For input requirements, result meanings and failure semantics, follow the
reference that matches the question:

- [component evaluation](../component-evaluation.md) for foldback, basal, paired
  stem, released-strand projection, and compiler integration;
- [processing discovery](../processing-discovery.md) for nick placement, exact
  precursor sequence, basal candidates, and terminal processing routes;
- [released-foldback routes](../released-foldback-routes.md) for joint geometry,
  exact selected precursors, and active/surviving-strand continuity; and
- [workflow views](../view-contracts.md) for renderer-independent projections.

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
[linear-source material reference](../linear-source-method-materials.md) and
[method boundary](../../methods/destination-neutrality.md). A complete request can be
written as a replay-verified method bundle containing the plan, trajectory,
FASTA, GenBank, and hairpin-encoding projection. Infeasible resolution raises
`MethodResolutionError` only when the caller requests that complete artifact
boundary; the lower-level compiler continues to return its typed outcome.

### File-oriented method operations

Callers with independent installations can use the
[external command and artifact interface](../external-artifacts.md). Its named
file operations preserve the authorities below while avoiding consumer Python
model imports.

The file-oriented operations in `hop_design.api` are
`resolve_linear_source_method_file(source)`,
`compile_linear_source_method_file(source, output)`, and
`verify_linear_source_method_file(bundle)`. They return the named method's
canonical authority report through the existing compiler and replay path.
`design_report(receipt)` serializes admitted design authorities and
producer-computed checks. `runtime_identity()` returns installation provenance
and the executing package-content digest. The
[external artifact reference](../external-artifacts.md) defines their authored
inputs, lineage bindings, and the distinction between recorded evidence and
fresh execution.

## Views

All operations and public contracts in this section use `hop_design.views`.

- `build_foldback_view(evaluation) -> WorkflowView`
- `build_foldback_junction_view(evaluation) -> WorkflowView`
- `build_released_workflow_view(state, foldback) -> WorkflowView`
- `build_basal_pairing_view(evaluation) -> WorkflowView`
- `build_basal_view(evaluation, nicked_strand=...) -> WorkflowView`
- `build_basal_source_panel(receipt, realization_id=...) -> ViewPanel`
- `build_method_trajectory_view(plan) -> WorkflowView`
- `render_workflow_svg(view) -> bytes`

The renderer consumes the typed view and performs no molecular derivation.
The same `hop_design.views` surface provides
`build_hairpin_junction_route_view(...)` and
`build_released_foldback_precursor_view(...)`; they are not package-root
exports.

`build_basal_source_panel` takes a verified local-neighborhood receipt and an
explicit local realization ID. It shows the source duplex, payload span,
nickase recognition sites, and nick boundary. A source-encoded recognition site
for later release is labeled separately; endpoint-supplied sites are omitted.
The panel does not assert strand removal, adapter joining, or future cleavage.
Unknown selections, non-basal receipts, and corrupt receipts raise `ValueError`.

The returned `ViewPanel` supports client figure composition or JSON export;
it is not a complete `WorkflowView` for `render_workflow_svg`. Both strand
sequences and feature coordinates are 5′→3′. Display the bottom track in reverse;
recognition spans use the source-top coordinate reference.

Stable package-root types cover payloads, design specs, coordinates, junctions,
processing agents, design results, and operator-facing errors. Discovery,
method, molecular-state, and view contracts live only on their named sibling
facades; the root does not forward them.
