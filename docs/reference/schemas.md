---
doc_id: hop-schema-reference
title: Current schema identifiers
intent: Identify supported source-checkout document types, their purpose, and their input limits.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: reference
journey:
  - compile
  - discover
  - method
  - verify
---

# Current schema identifiers

This table describes the source checkout, including unreleased construction
schemas. For the published `v0.1.0a8` wheel, use its
[tagged reference](https://github.com/e-south/hop-design/blob/v0.1.0a8/docs/reference/schemas.md).
The package version alone does not distinguish post-release source changes.

| Schema ID | Root model | Purpose |
| --- | --- | --- |
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
| `hop.construction-source/v7` | public file source | Strict foldback, optional PCR-basal, source-ssDNA preparation, endpoint-auxiliary resolution policies, whole-route constraints, and finite enumeration; the design bundle remains a separate verified path |
| `hop.source-partition-request/v2` | public file source | Exact source duplex, payload mapping, caller-provisioned enzyme domain, required survivor spans, preferred-to-absolute sacrificial-fragment maximum ladder, and finite subset-enumeration bounds |
| `hop.source-partition-policy/v1` | public file source | Enzyme provisioning, fragment-length rule, program width, and search bounds; the selected construction supplies the exact source and required survivors |
| `hop.source-partition-result/v2` | public discovery result | Replay-verified nick sites, full two-strand fragment certificates, threshold assessments, selected survivors, candidate dispositions, nick functions, and truthful completion status |
| `hop.source-partition-certificate/v1` | public construction projection | One explicitly selected, full-span two-strand fragment certificate with exact cleavage-boundary causes and the complete preferred-to-absolute threshold ladder |
| `hop.final-payload/v1` | internal construction model | Final-product payload coordinates, authored reference strand, boundaries, and derived pairing authority |
| `hop.local-neighborhood-request/v6` | internal construction model | Finite foldback or PCR-basal geometry domain, route, local endpoint, enzyme policy, retained-overhead ceiling, and search bounds |
| `hop.neighborhood-discovery-result/v5` | internal construction model | Shared retained-overhead accounting, geometry grouping, provenance, completion, feasibility, and termination semantics |
| `hop.foldback-neighborhood-result/v4` | portable local construction result | Replayable exact duplex foldback realizations with nick-strand, source-orientation, molecular lineage, and retained-overhead authorities |
| `hop.basal-neighborhood-result/v6` | portable local construction result | Replayable basal nick and proximal adapter-pairing realizations with retained-overhead, annealing-completion, and optional future-release obligations; full adapter materialization and PCR chronology remain whole-route concerns |
| `hop.construction-discovery-request/v6` | internal construction model | Verified design reference, local and optional selected source-partition references, source-ssDNA preparation policy, endpoint-auxiliary resolution policies, optional endpoint release, route constraints, and composition bounds |
| `hop.construction-space-result/v6` | internal construction model | Complete examined composition prefix, source-preparation and selected-partition authorities, resolved exact endpoint auxiliaries, exact accepted routes, endpoint products, material accounting, grouping, and claim boundary |
| `hop.construction-bundle/v5` | portable construction manifest | Content-addressed complete-construction result with source-preparation, selected-partition, and resolved-auxiliary authorities plus embedded verified design authority |
| `hop.foldback-feasibility-landscape/v3` | public construction projection | Every exact foldback realization from one unpartitioned search with its physical nick strand, source orientation, and achieved construction dimensions |
| `hop.foldback-feasibility-landscape/v4` | public construction projection | Every exact foldback realization from one declared sequence-domain part, with its part scope and achieved construction dimensions |
| `hop.basal-feasibility-landscape/v4` | public construction projection | Every exact basal realization from one unpartitioned search with its local nick, proximal pairing, annealing-completion, retained-overhead, warning, and optional future-release facts |
| `hop.basal-feasibility-landscape/v5` | public construction projection | Every exact basal realization from one declared sequence-domain part, with its part scope and local boundary obligations |
| `hop.basal-minimum-overhead-matrix/v1` | public construction projection | Proven local retained-overhead minima, complete infeasibility, or unresolved status for every declared basal nickase by future-release action cell |
| `hop.basal-minimum-overhead-matrix/v2` | public construction projection | The same basal cell relation for one declared sequence-domain part, with its exact part scope |
| `hop.foldback-overhead-frontier/v1` | public construction projection | Examined foldback retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.foldback-overhead-frontier/v2` | public construction projection | Examined foldback retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.basal-overhead-frontier/v1` | public construction projection | Examined basal retained-overhead levels from one unpartitioned search with complete or partial accounting |
| `hop.basal-overhead-frontier/v2` | public construction projection | Examined basal retained-overhead levels from one declared sequence-domain part with complete or partial accounting |
| `hop.complete-construction-summary/v3` | public construction projection | Lossless disposition, grouping, required external material, failure, and truncation relation over one verified complete result |
| `hop.construction-navigation/v1` | public construction projection | Summary v2 plus accepted-route geometry, retained-overhead accounting, cleavage-program enzyme IDs, retained non-payload sequence, endpoint topology, and reversible geometry membership |
| `hop.complete-construction-trajectory/v4` | public construction projection | One explicitly selected accepted realization with its source preparation, selected source-partition certificate when present, and exact molecular chronology |
| `hop.construction-selection/v1` | non-authoritative construction reference | One accepted materialized realization bound to its verified source result |
| `hop.linear-source-hairpin-pcr-materials/v1` | `LinearSourceHairpinPcrMaterialsSpec` | Six method oligos and ligation-end preparation |
| `hop.linear-source-hairpin-pcr-materials-plan/v1` | `LinearSourceHairpinPcrMaterialsPlan` | Derived terminal bindings and material handoff |
| `hop.linear-source-multinick-hairpin-pcr-request/v1` | `LinearSourceMultinickHairpinPcrRequest` | Exact method inputs, agents, selection, and projection |
| `hop.linear-source-multinick-hairpin-pcr-plan/v2` | `LinearSourceMultinickHairpinPcrPlan` | Complete molecular-state and product derivation with a replayable restriction agent |
| `hop.linear-source-multinick-hairpin-pcr-result/v2` | `LinearSourceMultinickHairpinPcrResult` | Orthogonal method outcome and optional plan |
| `hop.method-bundle/v2` | `MethodBundle` | Content-addressed method plan and artifacts |
| `hop.workflow-view/v1` | `WorkflowView` | Renderer-independent panels and tracks |

The construction source, source-partition request/result, construction bundle,
and six generated construction projection schemas are active external contracts through
`hop_design.construction`. The request and result schemas in that pipeline are
active replay authorities but remain internal: callers do not construct or
import their raw models through the public facade.

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

`hop.load_spec(path)` accepts only `.json`, `.yaml`, and `.yml`, and only the
two current single-design authored schemas. The scientist-facing CLI dispatches
`hop/substrate-space/v1` explicitly through `hop_design.spaces`; it does not
extend the single-design loader or guess from fields. Design spaces, catalogs,
plans, bundles, and workflow views use their own strict models or integrity
operations.

Breaking-history rationale belongs in the [decision index](../architecture/decisions/README.md),
not in the active schema contract.

The listed construction schemas form one fail-closed cut and accept no retired
source, request, result, or bundle version. The named-method v1 material
schemas remain a separate exact-method contract and retain their exact oligo
fields.
