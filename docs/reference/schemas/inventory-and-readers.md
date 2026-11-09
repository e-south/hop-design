# Schema inventory and reader contracts

Identify active schema IDs and the reader, size, coordinate and replay contracts that
govern their admission.

Return to the [schemas reference](../schemas.md).

## Schema inventory

This inventory covers `v0.1.0a9`. For the earlier `v0.1.0a8` package, use its
[tagged reference](https://github.com/e-south/hop-design/blob/v0.1.0a8/docs/reference/schemas.md).
The package version alone does not distinguish post-release source changes.

| Schema ID | Root model | Purpose |
| --- | --- | --- |
| `hop.construction-request-preview/v1` | non-authoritative authoring preview | Request digest, end footprint, explicit pairing permissions, annealing minimum and optional reference diff; no search or feasibility claim |
| `hop.request-execution-report/v1` | non-authoritative outcome report | Scope, stage, local coverage, selected continuation and pointers to preserved authorities; not a molecular result schema |
| `hop/substrate-space/v1` | `SubstrateSpaceSpec` | One labeled fixed-and-variable authored payload arm with an optional question |
| `hop.hairpin-design-set/v2` | `HairpinDesignSet` | Complete content-addressed digital design-set manifest |
| `hop.molecular-substrate-space/v1` | `MolecularSubstrateSpace` | Normalized per-position molecular authority for one substrate space |
| `hop.design/v2` | `HopSpec` | Named generic design intent |
| `hop.resolved-design/v2` | `ResolvedHopSpec` | Explicit caller-supplied components and design derivation |
| `hop.plan/v3` | `HopPlan` | Immutable compiler-owned design derivation and encoding |
| `hop.bundle/v2` | `HopBundle` | Content-addressed design artifact manifest |
| `hop.provenance/v2` | `ProvenanceRecord` | Compiler and design-reference lock |
| `hop.resolved-design-space/v2` | `ResolvedDesignSpace` | Bounded composable payload and component axes |
| `hop.design-space-plan/v2` | `DesignSpacePlan` | Renderer-free checked Cartesian review table |
| `hop.processing-catalog/v1` | `ProcessingCatalog` | Caller-supplied nicking and release agents |
| `hop.foldback-precursor-search/v1` | `FoldbackPrecursorSearchRequest` | Exact precursor materialization after placement |
| `hop.basal-candidate-search/v2` | `BasalCandidateSearchRequest` | Bounded basal arm domains and explicit heuristic-index policy |
| `hop.basal-processing-geometry-request/v1` | `BasalProcessingGeometryRequest` | Terminal processing geometry query |
| `hop.basal-processing-route-search-result/v2` | `BasalProcessingRouteSearchResult` | Bounded basal pair and processing join |
| `hop.released-foldback-geometry-request/v1` | `ReleasedFoldbackGeometryRequest` | Cross-agent foldback target and boundary window |
| `hop.released-foldback-geometry-search-result/v1` | `ReleasedFoldbackGeometrySearchResult` | Replayable geometry domains and completion evidence |
| `hop.released-foldback-precursor-search-request/v1` | `ReleasedFoldbackPrecursorSearchRequest` | Selected geometry and caller precursor domain |
| `hop.released-foldback-precursor-search-result/v1` | `ReleasedFoldbackPrecursorSearchResult` | Bounded exact precursor materialization |
| `hop.hairpin-junction-route-search-result/v2` | `HairpinJunctionRouteSearchResult` | Bounded continuity join across junction processes |
| `hop.construction-source/v8` | public file source | Strict foldback, optional PCR-basal, source-ssDNA preparation, endpoint-auxiliary resolution policies, whole-route constraints, and finite enumeration; the design bundle remains a separate verified path |
| `hop.source-partition-request/v2` | public file source | Exact source duplex, payload mapping, caller-provisioned enzyme domain, required survivor spans, preferred-to-absolute sacrificial-fragment maximum ladder, and finite subset-enumeration bounds |
| `hop.source-partition-policy/v1` | public file source | Enzyme provisioning, fragment-length rule, program width, and search bounds; the selected construction supplies the exact source and required survivors |
| `hop.source-partition-result/v2` | public discovery result | Replay-verified nick sites, full two-strand fragment certificates, threshold assessments, selected survivors, candidate dispositions, nick functions, and truthful completion status |
| `hop.source-partition-certificate/v1` | public construction projection | One explicitly selected, full-span two-strand fragment certificate with exact cleavage-boundary causes and the complete preferred-to-absolute threshold ladder |
| `hop.final-payload/v1` | internal construction model | Final-product payload coordinates, authored reference strand, boundaries, and derived pairing authority |
| `hop.local-neighborhood-request/v7` | internal construction model | Finite foldback or PCR-basal geometry domain, route, local endpoint, enzyme policy, retained-overhead ceiling, and search bounds |
| `hop.neighborhood-discovery-result/v6` | internal construction model | Shared retained-overhead accounting, geometry grouping, provenance, completion, feasibility, and termination semantics |
| `hop.foldback-neighborhood-result/v5` | portable local construction result | Replayable exact duplex foldback realizations with nick-strand, source-orientation, molecular lineage, and retained-overhead authorities |
| `hop.foldback-sequence-request/v1` | public file source | Payload, finite geometry domain, enzyme policy, retained-path ceiling, and explicit compact execution bounds |
| `hop.foldback-sequence-result/v2` | portable local construction result | Complete retained populations and joint source assignments, raw retained denominators, placement exclusions, program support, and deduplicated retained unions |
| `hop.foldback-sequence-member/v2` | public member report | Selected retained sequence, supporting program and indexed source-tail completion recovered through full molecular realization |
| `hop.basal-sequence-request/v1` | public file source | Payload, canonical basal geometry, endpoint, enzyme policy, local-span ceiling, and compact execution bounds |
| `hop.basal-sequence-result/v1` | portable local construction result | Complete local populations, raw denominators, full-source support, and deduplicated local unions |
| `hop.basal-sequence-member/v1` | public member report | A selected local word and supporting source recovered through ordinary basal molecular realization |
| `hop.sequence-set/v1` | embedded exact DNA set | Canonical reduced A/C/G/T decisions, exact cardinality, and recoverable independent-base membership |
| `hop.basal-neighborhood-result/v7` | portable local construction result | Replayable basal nick and proximal adapter-pairing realizations with retained-overhead, annealing-completion, and optional future-release obligations; full adapter materialization and PCR chronology remain whole-route concerns |
| `hop.construction-discovery-request/v7` | internal construction model | Verified design reference, local and optional selected source-partition references, source-ssDNA preparation policy, endpoint-auxiliary resolution policies, optional endpoint release, route constraints, and composition bounds |
| `hop.construction-space-result/v9` | internal construction model | Complete examined composition prefix, typed preparation-constraint diagnostics, source-preparation and selected-partition authorities, resolved exact endpoint auxiliaries, exact accepted routes, endpoint products, material accounting, grouping, and claim boundary |
| `hop.construction-bundle/v6` | portable construction manifest | Content-addressed complete-construction result with source-preparation, selected-partition, and resolved-auxiliary authorities plus embedded verified design authority |
| `hop.foldback-feasibility-landscape/v5` | public construction projection | Every exact foldback realization from one unpartitioned search with its physical nick strand, source orientation, and achieved construction dimensions |
| `hop.foldback-feasibility-landscape/v6` | public construction projection | Every exact foldback realization from one declared sequence-domain part, with its part scope and achieved construction dimensions |
| `hop.basal-feasibility-landscape/v6` | public construction projection | Every exact basal realization from one unpartitioned search with its local nick, proximal pairing, annealing-completion, retained-overhead, warning, and optional future-release facts |
| `hop.basal-feasibility-landscape/v7` | public construction projection | Every exact basal realization from one declared sequence-domain part, with its part scope and local boundary obligations |
| `hop.basal-minimum-overhead-matrix/v3` | public construction projection | Proven local retained-overhead minima, complete infeasibility, or unresolved status for every declared basal nickase by future-release action cell |
| `hop.basal-minimum-overhead-matrix/v4` | public construction projection | The same basal cell relation for one declared sequence-domain part, with its exact part scope |
| `hop.foldback-overhead-frontier/v1` | public construction projection | Examined foldback retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.foldback-overhead-frontier/v2` | public construction projection | Examined foldback retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.basal-overhead-frontier/v1` | public construction projection | Examined basal retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.basal-overhead-frontier/v2` | public construction projection | Examined basal retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.complete-construction-summary/v5` | public construction projection | Lossless disposition, grouping, required external material, failure, and truncation relation over one verified complete result |
| `hop.construction-navigation/v2` | public construction projection | Summary v5 plus accepted-route geometry, retained-overhead accounting, cleavage-program enzyme IDs, retained non-payload sequence, endpoint topology, and reversible geometry membership |
| `hop.complete-construction-trajectory/v5` | public construction projection | One explicitly selected accepted realization with its source preparation, selected source-partition certificate when present, and exact molecular chronology |
| `hop.construction-selection/v1` | non-authoritative construction reference | One accepted materialized realization bound to its verified source result |
| `hop.hairpin-portrait/v1` | public construction projection | One selected joined hairpin with actual pairing geometry, joins, terminal chemistry and separately staged release interfaces |
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Exact method inputs, agents, selection, and projection |
| `hop.linear-source-multinick-hairpin-pcr-plan/v2` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and product derivation with a replayable restriction agent |
| `hop.linear-source-multinick-hairpin-pcr-result/v2` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional plan |
| `hop.method-bundle/v2` | `MethodBundle` | Content-addressed method plan and artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |
| `hop.recorded-design-source/v1` | `RecordedDesignSource` | Original producer, snapshot, SHA-256 and byte-size bindings for explicit read-only compact capture |
| `hop.recorded-capture-origin/v1` | capture provenance | Source contract and separately identified exporter; bound by the immutable edition manifest |

The construction source, source-partition request/result, construction bundle,
and generated construction projection schemas are active external contracts through
`hop_design.construction`. The request and result schemas in that pipeline are
active replay authorities but remain internal: callers do not construct or
import their raw models through the public facade.

The optional `whole_route_constraints.hairpin_scaffold` object specifies
inclusive `minimum`/`maximum` ranges for `open_side_paired_positions`,
`loop_side_paired_bp` and `loop_nt`. Missing dimensions are unconstrained;
equal boundaries are exact values. It is carried into complete request identity.
An out-of-range complete candidate has rejection code
`hairpin-scaffold-outside-request`, exact `scaffold_mismatches`, and retained
`scaffold_rejection_candidates` for replay. Empty optional fields are omitted,
preserving existing unconstrained request/result bytes. Older readers that
do not support these fields reject them; no compatibility conversion occurs.

Authored construction and local-neighborhood source documents are limited to
one megabyte. Public local-neighborhood requests may declare at most 100,000
search nodes and 100,000 realizations. Portable local-neighborhood result JSON
is bounded separately at 64 MiB because it records complete candidate,
rejection, and replay evidence. Result loading enforces the embedded execution
limits before replay. Searches that would exceed either envelope may use a
declared canonical `sequence_partition` of 2 through 256 parts. Every part is a
replayable local authority over a deterministic, disjoint portion of the exact
sequence domain; realization and construction-problem identities remain
unchanged. A part may be complete for its declared domain but reports
whole-domain payload compatibility as `not_computed`. Partitioning is
incompatible with all-member compatibility constraints. A caller must
verify every ordered part, reject truncation,
and prove pairwise-disjoint realization membership before describing the family
as an exhaustive aggregate. HOP never silently narrows or publishes an
undeclared partial local authority.

`hop.foldback-nucleotide-exemplar/v1` and
`hop.foldback-geometry-count-table/v1` are reserved projection identifiers in
the foldback inventory. No current public model, renderer, or reader accepts
them, and an inventory entry marked `not_generated` is not an artifact claim.

Serialized documents use the JSON key `schema`. Exact IDs are dispatch
contracts: unknown or retired versions fail and are never interpreted as the
nearest known schema. Public models are strict, frozen, and reject unknown
fields. HOP provides no old-version readers, aliases, or artifact-name fallback.

Current basal future-release and complete release-side requirements mandate
`payload_end_offset_bp`. The source, local request, embedded neighborhood,
family result, complete request/result/bundle, and dependent projection schemas
bind this coordinate contract explicitly. Historical artifacts require their
recorded producer; the current runtime does not supply a missing zero offset.

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two current single-design authored schemas. The CLI dispatches
`hop/substrate-space/v1` explicitly through `hop_design.spaces`; it does not
extend the single-design loader or guess from fields. Design spaces, catalogs,
plans, bundles, and workflow views use their own strict models or integrity
operations.

Breaking-history rationale belongs in the [decision index](../../architecture/decisions/README.md),
not in the active schema contract.

Current construction readers accept only the listed active source, request,
result and bundle versions. They reject retired versions. The
named-method v1 material schemas remain a separate exact-method contract and
retain their exact oligo fields.

The current development cut uses construction-space-result v9 and complete-route
implementation 11. Released inserts carry `release_evidence` with a source-anchored
hairpin-core projection in the PCR parent, the actual released union, and the
retained span on each parent strand. These are distinct coordinate records: a
release may retain additional construction sequence or remove outer core bases,
while preserving both supplied-stem copies and the intervening foldback on both
strands. Unreleased endpoints retain their endpoint `encoding_projection`.
Supplying both forms, neither form, or the retired clone encoding-only form fails.

Replay independently derives the core occurrence from the source and primer
extension, and the retained spans from the four cuts. PCR sequence-fate spans
follow those per-strand retention boundaries. Complete summary v5 still seals
violated preparation constraints into replay; diagnostics report evaluated
constraints, not minimal conflicts or necessary repairs. Retired v8/implementation
10 bundles require their recorded producer or regeneration from preserved inputs.
Do not relabel old authorities. See [ADR 0053](../../architecture/decisions/0053-separate-hairpin-core-and-insert-release.md).

Scaffold-family inputs use `hop.construction-family/v1`: one strict product
request, 1–64 explicitly named variations, shared properties, optional display
preferences and aggregate execution bounds. `hop.construction-family-preview/v3`
and `hop.construction-family-result/v1` summarize expansion and per-member
execution; `hop.construction-family-packet/v1` hashes packet artifacts. A packet
manifest excludes itself. Existing local/design/construction authorities retain
molecular and coverage meaning.

`hop.construction-set/v1` names explicit complete selections, baseline, shared
and compared properties. `hop.construction-set-summary/v2` binds resolved
identities and properties; `hop.construction-set-packet/v1` inventories portable
member authorities, portraits, preparations, comparisons and consolidated
chemical order specifications. Absolute input paths are not part of set identity.
Reopening portable membership repeats authority verification. No set-manifest
reader is introduced as an alternative to that replay.

`hop.construction-comparison/v2` binds two exact selections and recorded property
differences, including region sequences, absolute spans, local contacts and
material-role changes. The human label and machine field are separate entries.
The projection is derived evidence, not a complete molecular authority.


`hop.scaffold-comparison/v1` compiles a product/vary/hold brief to the existing
family request. `hop.construction-family-result/v2` records explicitly reconciled
continuations and parent lineage; ordinary execution remains v1. Report v3 adds
separate family/selected-set molecular controls and explicit recovery facts. Molecular authority
schemas and IDs remain unchanged. See [ADR 0039](../../architecture/decisions/0039-scaffold-comparison-and-revision.md).


The family and set shared-property vocabulary also accepts `non_loop_sequences`,
`regional_contacts` and `regional_joins`. These bind region-local molecular facts
and stage, independently of absolute-coordinate movement and preparation changes.
Set summary v2 uses set identity version 2. Report v3 keeps required agreement,
observed agreement, differences and missing evidence distinct. Existing immutable
family and molecular records are not rewritten; regenerate only derived views.
See [ADR 0040](../../architecture/decisions/0040-explicit-comparison-controls.md).

`hop.construction-family-preview/v3` records all dimension-level conflicts with
canonical declaration paths and explicit edit options. Its `preview.svg` depicts
intent, not a completed molecule. Earlier previews remain historical artifacts.
`hop.family-matching-result/v1` records the declared complete reference,
original and continued choices, shared-property agreement and bounded coverage.
`hop.family-matching-packet/v1` hashes its portable evidence inventory; underlying
molecular authorities remain unchanged. See
[ADR 0041](../../architecture/decisions/0041-reference-bound-family-matching.md).
